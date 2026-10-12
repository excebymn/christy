//! christy: the core of a personal CLI ecosystem.
//!
//! One entry point for personal tools. The core only discovers tools (via
//! their `manifest.toml`), checks what they need, offers their own setup
//! script when something is missing, and then `exec`s them.

mod cli;
mod commands;
mod deps;
mod error;
mod fsutil;
mod manifest;
mod messages;
mod paths;
mod prompt;
mod registry;
mod runtime;
mod setup;
mod signals;
mod suggest;
mod term;

use std::env;
use std::process::ExitCode;

use cli::Command;
use commands::help::ToolSection;
use error::CoreError;
use paths::Paths;

fn main() -> ExitCode {
    signals::restore_sigpipe();
    match run() {
        Ok(code) => exit_code(code),
        Err(err) => {
            err.report();
            exit_code(err.exit_code())
        }
    }
}

fn exit_code(code: i32) -> ExitCode {
    ExitCode::from(u8::try_from(code).unwrap_or(1))
}

fn run() -> Result<i32, CoreError> {
    match cli::parse(env::args_os().skip(1).collect())? {
        Command::Version => {
            println!("{}", messages::version_line());
            Ok(0)
        }
        Command::Help => {
            commands::help::print(&load_tool_section());
            Ok(0)
        }
        Command::List => commands::list::run(&Paths::resolve()?),
        Command::HelpFor(name) => commands::run::help(&name),
        Command::Tool { name, args } => commands::run::run(&name, args),
        Command::Doctor => commands::doctor::run(),
        Command::Setup(name) => commands::setup::run(name.as_deref()),
        Command::Update => commands::update::run(),
    }
}

/// Best effort: help should work even before a repo is configured.
fn load_tool_section() -> ToolSection {
    let loaded = Paths::resolve().and_then(|paths| registry::load_or_build(&paths));
    match loaded {
        Ok(registry) => ToolSection::Loaded(
            registry
                .valid_tools()
                .map(|tool| (tool.name.clone(), tool.description.clone()))
                .collect(),
        ),
        Err(err) => ToolSection::Unavailable(err.to_string()),
    }
}
