//! Yes/no prompts. They talk on stderr so a tool's stdout stays clean, and
//! they only run when a person is actually there to answer.

use std::io::{self, BufRead, IsTerminal, Write};

use crate::messages as msg;

const MAX_ATTEMPTS: usize = 3;

/// A prompt is only possible with a terminal on both input and output.
pub fn is_interactive() -> bool {
    io::stdin().is_terminal() && io::stderr().is_terminal()
}

/// Asks until it gets a clear answer. Empty input picks the default; end of
/// input or too many unclear answers count as "no".
pub fn confirm(question: &str, default_yes: bool) -> bool {
    let suffix = if default_yes { "[Y/n]" } else { "[y/N]" };
    let stdin = io::stdin();
    let mut lines = stdin.lock().lines();

    for _ in 0..MAX_ATTEMPTS {
        eprint!("{question} {suffix} ");
        let _ = io::stderr().flush();

        let Some(Ok(line)) = lines.next() else {
            eprintln!();
            return false;
        };
        match parse_answer(&line, default_yes) {
            Some(answer) => return answer,
            None => eprintln!("{}", msg::PROMPT_UNCLEAR),
        }
    }
    false
}

fn parse_answer(input: &str, default_yes: bool) -> Option<bool> {
    match input.trim().to_lowercase().as_str() {
        "" => Some(default_yes),
        "y" | "yes" => Some(true),
        "n" | "no" => Some(false),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn answers_are_parsed_leniently() {
        assert_eq!(parse_answer("", true), Some(true));
        assert_eq!(parse_answer("", false), Some(false));
        assert_eq!(parse_answer(" Y ", false), Some(true));
        assert_eq!(parse_answer("yes", false), Some(true));
        assert_eq!(parse_answer("No", true), Some(false));
        assert_eq!(parse_answer("maybe", true), None);
    }
}
