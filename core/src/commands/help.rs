//! `christy -h` / `christy help`: built-in commands plus the tools found in
//! the registry. Each tool owns its own help (`christy <tool> -h`).

use crate::messages as msg;
use crate::term::Painter;

/// The tool list can fail to load (no repo yet, broken tools/ folder). Help
/// must still work then, so the section degrades instead of erroring.
pub enum ToolSection {
    Loaded(Vec<(String, String)>),
    Unavailable(String),
}

pub fn print(tools: &ToolSection) {
    println!("{}", render(&Painter::stdout(), tools));
}

pub fn render(painter: &Painter, tools: &ToolSection) -> String {
    let width = label_width(tools);
    let mut out = String::new();

    out.push_str(&format!(
        "{} {}\n{}\n",
        painter.bold("christy"),
        env!("CARGO_PKG_VERSION"),
        msg::HELP_TAGLINE
    ));

    out.push_str(&format!("\n{}\n", painter.bold(msg::HELP_SECTION_USAGE)));
    for line in msg::HELP_USAGE_LINES {
        out.push_str(&format!("  {line}\n"));
    }

    out.push_str(&format!("\n{}\n", painter.bold(msg::HELP_SECTION_COMMANDS)));
    for (label, text) in msg::HELP_COMMANDS {
        out.push_str(&row(painter, label, width, text));
    }

    out.push_str(&format!("\n{}\n", painter.bold(msg::HELP_SECTION_OPTIONS)));
    for (label, text) in msg::HELP_OPTIONS {
        out.push_str(&row(painter, label, width, text));
    }

    out.push_str(&format!("\n{}\n", painter.bold(msg::HELP_SECTION_TOOLS)));
    match tools {
        ToolSection::Loaded(list) if list.is_empty() => {
            out.push_str(&format!("  {}\n", painter.dim(msg::HELP_NO_TOOLS)));
        }
        ToolSection::Loaded(list) => {
            for (name, description) in list {
                out.push_str(&row(painter, name, width, description));
            }
        }
        ToolSection::Unavailable(reason) => {
            out.push_str(&format!(
                "  {}\n",
                painter.yellow(&msg::help_tools_unavailable(reason))
            ));
        }
    }

    out.trim_end().to_string()
}

fn row(painter: &Painter, label: &str, width: usize, text: &str) -> String {
    format!("  {}  {text}\n", painter.cyan(&format!("{label:<width$}")))
}

/// One shared column width so commands, options, and tools line up together.
fn label_width(tools: &ToolSection) -> usize {
    let builtin = msg::HELP_COMMANDS
        .iter()
        .chain(msg::HELP_OPTIONS.iter())
        .map(|(label, _)| label.chars().count());
    let tool_names = match tools {
        ToolSection::Loaded(list) => list.iter().map(|(name, _)| name.chars().count()).collect(),
        ToolSection::Unavailable(_) => Vec::new(),
    };
    builtin.chain(tool_names).max().unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lists_commands_and_tools_aligned() {
        let tools = ToolSection::Loaded(vec![("cleanmeta".into(), "Wipe metadata".into())]);
        let text = render(&Painter::plain(), &tools);
        assert!(text.contains("USAGE"));
        // Widest label is "-V, --version" (13 chars), shared by every section.
        assert!(text.contains(&format!("  {:<13}  show available tools", "list")));
        assert!(text.contains(&format!("  {:<13}  Wipe metadata", "cleanmeta")));
    }

    #[test]
    fn degrades_when_tools_cannot_load() {
        let text = render(&Painter::plain(), &ToolSection::Unavailable("boom".into()));
        assert!(text.contains("couldn't load the tool list (boom)"));
        assert!(text.contains("COMMANDS"));
    }

    #[test]
    fn empty_tool_list_is_explained() {
        let text = render(&Painter::plain(), &ToolSection::Loaded(Vec::new()));
        assert!(text.contains("no tools found yet"));
    }
}
