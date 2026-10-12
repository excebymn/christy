//! Turns manifest text into a `Manifest`, checking `schema` first so a
//! manifest written for a newer core fails with a clear message.

use super::types::Manifest;
use crate::messages as msg;

pub const SUPPORTED_SCHEMA: u32 = 1;

pub fn parse(text: &str) -> Result<Manifest, Vec<String>> {
    let value: toml::Value = text
        .parse()
        .map_err(|err: toml::de::Error| vec![msg::manifest_syntax(err.message())])?;

    match value.get("schema").and_then(toml::Value::as_integer) {
        None => return Err(vec![msg::manifest_schema_missing()]),
        Some(found) if found < 1 || found > i64::from(SUPPORTED_SCHEMA) => {
            return Err(vec![msg::manifest_schema_unsupported(found, SUPPORTED_SCHEMA)]);
        }
        Some(_) => {}
    }

    value
        .try_into::<Manifest>()
        .map_err(|err| vec![msg::manifest_invalid(err.message())])
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::manifest::types::Runtime;

    const CLEANMETA: &str = r#"
schema = 1
name = "cleanmeta"
version = "0.2.0"
description = "Wipe hidden metadata from images, documents, and code files"
runtime = "python"
entry = "main.py"
platforms = ["linux"]

[requires]
bins = ["python3"]

[setup]
script = "setup.sh"
"#;

    #[test]
    fn parses_the_real_cleanmeta_manifest() {
        let manifest = parse(CLEANMETA).expect("should parse");
        assert_eq!(manifest.name, "cleanmeta");
        assert_eq!(manifest.runtime, Runtime::Python);
        assert_eq!(manifest.requires.bins, vec!["python3"]);
        assert_eq!(manifest.setup.unwrap().script, "setup.sh");
    }

    #[test]
    fn optional_sections_can_be_omitted() {
        let text = "schema = 1\nname = \"a\"\ndescription = \"d\"\nruntime = \"bash\"\nentry = \"run.sh\"\n";
        let manifest = parse(text).expect("should parse");
        assert!(manifest.requires.bins.is_empty());
        assert!(manifest.setup.is_none());
        assert!(manifest.version.is_none());
    }

    #[test]
    fn missing_schema_is_reported() {
        let errs = parse("name = \"a\"").unwrap_err();
        assert!(errs[0].contains("schema"));
    }

    #[test]
    fn newer_schema_is_rejected_with_a_clear_message() {
        let errs = parse("schema = 2\nname = \"a\"").unwrap_err();
        assert!(errs[0].contains("only understands up to schema 1"));
    }

    #[test]
    fn typos_in_field_names_are_caught() {
        let text = CLEANMETA.replace("[requires]", "[requries]");
        let errs = parse(&text).unwrap_err();
        assert!(errs[0].contains("requries"));
    }

    #[test]
    fn unknown_runtime_is_rejected() {
        let text = CLEANMETA.replace("python", "cobol");
        assert!(parse(&text).is_err());
    }

    #[test]
    fn broken_toml_is_reported() {
        assert!(parse("schema = ").is_err());
    }
}
