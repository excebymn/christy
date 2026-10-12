//! Minimal ANSI styling. Colors are on only when the stream is a terminal
//! and NO_COLOR is unset, so piped output stays clean.

use std::env;
use std::io::IsTerminal;

#[derive(Debug, Clone, Copy)]
pub struct Painter {
    enabled: bool,
}

impl Painter {
    pub fn stdout() -> Self {
        Self {
            enabled: std::io::stdout().is_terminal() && color_allowed(),
        }
    }

    pub fn stderr() -> Self {
        Self {
            enabled: std::io::stderr().is_terminal() && color_allowed(),
        }
    }

    #[cfg(test)]
    pub fn plain() -> Self {
        Self { enabled: false }
    }

    fn paint(&self, code: &str, text: &str) -> String {
        if self.enabled {
            format!("\x1b[{code}m{text}\x1b[0m")
        } else {
            text.to_string()
        }
    }

    pub fn bold(&self, text: &str) -> String {
        self.paint("1", text)
    }

    pub fn dim(&self, text: &str) -> String {
        self.paint("2", text)
    }

    pub fn red(&self, text: &str) -> String {
        self.paint("31", text)
    }

    pub fn green(&self, text: &str) -> String {
        self.paint("32", text)
    }

    pub fn yellow(&self, text: &str) -> String {
        self.paint("33", text)
    }

    pub fn cyan(&self, text: &str) -> String {
        self.paint("36", text)
    }
}

fn color_allowed() -> bool {
    env::var_os("NO_COLOR").map_or(true, |value| value.is_empty())
}
