//! `christy list`: a table of every valid tool, plus a pointer to `doctor`
//! when some tools have problems.

use crate::error::CoreError;
use crate::manifest::Manifest;
use crate::messages as msg;
use crate::paths::Paths;
use crate::registry;
use crate::term::Painter;

pub fn run(paths: &Paths) -> Result<i32, CoreError> {
    let registry = registry::load_or_build(paths)?;
    let painter = Painter::stdout();

    let tools: Vec<&Manifest> = registry.valid_tools().collect();
    if tools.is_empty() {
        println!("{}", msg::list_no_tools(&paths.tools_dir));
    } else {
        print!("{}", render_table(&painter, &tools));
    }

    let problems = registry.invalid_count();
    if problems > 0 {
        println!("\n{}", painter.yellow(&msg::list_problems(problems)));
    }
    Ok(0)
}

fn render_table(painter: &Painter, tools: &[&Manifest]) -> String {
    let version_of = |tool: &Manifest| -> String {
        tool.version
            .clone()
            .unwrap_or_else(|| msg::LIST_NO_VERSION.to_string())
    };

    let name_w = column_width(msg::LIST_COL_NAME, tools.iter().map(|t| t.name.as_str()));
    let version_w = column_width(
        msg::LIST_COL_VERSION,
        tools.iter().map(|t| version_of(t)).collect::<Vec<_>>().iter().map(String::as_str),
    );
    let runtime_w = column_width(
        msg::LIST_COL_RUNTIME,
        tools.iter().map(|t| t.runtime.as_str()),
    );

    let mut out = String::new();
    let header = format!(
        "{:<name_w$}  {:<version_w$}  {:<runtime_w$}  {}",
        msg::LIST_COL_NAME,
        msg::LIST_COL_VERSION,
        msg::LIST_COL_RUNTIME,
        msg::LIST_COL_DESCRIPTION,
    );
    out.push_str(&painter.dim(&header));
    out.push('\n');

    for tool in tools {
        out.push_str(&format!(
            "{}  {:<version_w$}  {:<runtime_w$}  {}\n",
            painter.cyan(&format!("{:<name_w$}", tool.name)),
            version_of(tool),
            tool.runtime.as_str(),
            tool.description,
        ));
    }
    out
}

fn column_width<'a>(header: &str, values: impl Iterator<Item = &'a str>) -> usize {
    values
        .map(|value| value.chars().count())
        .chain(std::iter::once(header.chars().count()))
        .max()
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::manifest::parse;

    fn tool(name: &str, version: Option<&str>) -> Manifest {
        let version_line = version.map_or(String::new(), |v| format!("version = \"{v}\"\n"));
        parse(&format!(
            "schema = 1\nname = \"{name}\"\n{version_line}description = \"d-{name}\"\nruntime = \"bash\"\nentry = \"x\"\n"
        ))
        .unwrap()
    }

    #[test]
    fn table_aligns_columns_and_fills_missing_versions() {
        let a = tool("cleanmeta", Some("0.2.0"));
        let b = tool("sys", None);
        let text = render_table(&Painter::plain(), &[&a, &b]);
        let lines: Vec<&str> = text.lines().collect();
        assert_eq!(lines[0], "NAME       VERSION  RUNTIME  DESCRIPTION");
        assert_eq!(lines[1], "cleanmeta  0.2.0    bash     d-cleanmeta");
        assert_eq!(lines[2], "sys        -        bash     d-sys");
    }
}
