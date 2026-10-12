//! Hand-rolled argument parsing.
//!
//! Everything after a tool's name is passed through untouched (including
//! `-h`), so a full parser library would only get in the way. Only the first
//! argument decides what happens.

use std::ffi::OsString;

use crate::error::CoreError;
use crate::messages as msg;

#[derive(Debug, PartialEq, Eq)]
pub enum Command {
    Help,
    HelpFor(String),
    Version,
    List,
    Doctor,
    Setup(Option<String>),
    Update,
    Tool { name: String, args: Vec<OsString> },
}

pub fn parse(args: Vec<OsString>) -> Result<Command, CoreError> {
    let Some(first) = args.first() else {
        return Ok(Command::Help);
    };
    let first = first
        .to_str()
        .ok_or_else(|| CoreError::Usage(msg::usage_not_utf8()))?
        .to_string();
    let rest = &args[1..];

    match first.as_str() {
        "-h" | "--help" => Ok(Command::Help),
        "help" => match rest.first() {
            None => Ok(Command::Help),
            Some(name) => Ok(Command::HelpFor(utf8(name)?)),
        },
        "-V" | "--version" | "version" => Ok(Command::Version),
        "list" => no_arguments("list", rest, Command::List),
        "doctor" => no_arguments("doctor", rest, Command::Doctor),
        "update" => no_arguments("update", rest, Command::Update),
        "setup" => match rest {
            [] => Ok(Command::Setup(None)),
            [name] => Ok(Command::Setup(Some(utf8(name)?))),
            _ => Err(CoreError::Usage(msg::usage_setup_too_many())),
        },
        option if option.starts_with('-') => {
            Err(CoreError::Usage(msg::usage_unknown_option(option)))
        }
        _ => Ok(Command::Tool {
            name: first,
            args: rest.to_vec(),
        }),
    }
}

fn no_arguments(name: &str, rest: &[OsString], command: Command) -> Result<Command, CoreError> {
    if rest.is_empty() {
        Ok(command)
    } else {
        Err(CoreError::Usage(msg::usage_no_arguments(name)))
    }
}

fn utf8(value: &OsString) -> Result<String, CoreError> {
    value
        .to_str()
        .map(str::to_string)
        .ok_or_else(|| CoreError::Usage(msg::usage_not_utf8()))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parse_strs(args: &[&str]) -> Result<Command, CoreError> {
        parse(args.iter().map(OsString::from).collect())
    }

    #[test]
    fn no_arguments_shows_help() {
        assert_eq!(parse_strs(&[]).unwrap(), Command::Help);
    }

    #[test]
    fn help_flags_and_command() {
        assert_eq!(parse_strs(&["-h"]).unwrap(), Command::Help);
        assert_eq!(parse_strs(&["--help"]).unwrap(), Command::Help);
        assert_eq!(parse_strs(&["help"]).unwrap(), Command::Help);
        assert_eq!(
            parse_strs(&["help", "cleanmeta"]).unwrap(),
            Command::HelpFor("cleanmeta".into())
        );
    }

    #[test]
    fn version_forms() {
        for form in ["-V", "--version", "version"] {
            assert_eq!(parse_strs(&[form]).unwrap(), Command::Version);
        }
    }

    #[test]
    fn built_ins_reject_stray_arguments() {
        assert!(matches!(parse_strs(&["list", "x"]), Err(CoreError::Usage(_))));
        assert!(matches!(parse_strs(&["setup", "a", "b"]), Err(CoreError::Usage(_))));
        assert_eq!(parse_strs(&["setup"]).unwrap(), Command::Setup(None));
        assert_eq!(
            parse_strs(&["setup", "cleanmeta"]).unwrap(),
            Command::Setup(Some("cleanmeta".into()))
        );
    }

    #[test]
    fn unknown_options_are_usage_errors() {
        let err = parse_strs(&["--nope"]).unwrap_err();
        assert_eq!(err.exit_code(), 2);
    }

    #[test]
    fn tool_arguments_pass_through_untouched() {
        let command = parse_strs(&["cleanmeta", "-h", "--types", "image", "photos"]).unwrap();
        assert_eq!(
            command,
            Command::Tool {
                name: "cleanmeta".into(),
                args: vec!["-h".into(), "--types".into(), "image".into(), "photos".into()],
            }
        );
    }
}
