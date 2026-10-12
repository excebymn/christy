//! "Did you mean...?" for mistyped tool and command names.

/// Up to three candidates close to `input`, closest first.
pub fn closest<'a>(input: &str, candidates: impl Iterator<Item = &'a str>) -> Vec<String> {
    let limit = (input.chars().count() / 3).max(2);
    let mut scored: Vec<(usize, &str)> = candidates
        .map(|candidate| (edit_distance(input, candidate), candidate))
        .filter(|(distance, _)| *distance <= limit)
        .collect();
    scored.sort_by(|a, b| a.0.cmp(&b.0).then(a.1.cmp(b.1)));
    scored.dedup_by(|a, b| a.1 == b.1);
    scored
        .into_iter()
        .take(3)
        .map(|(_, name)| name.to_string())
        .collect()
}

/// Classic Levenshtein distance with a single rolling row.
fn edit_distance(a: &str, b: &str) -> usize {
    let a: Vec<char> = a.chars().collect();
    let b: Vec<char> = b.chars().collect();
    let mut row: Vec<usize> = (0..=b.len()).collect();

    for (i, ca) in a.iter().enumerate() {
        let mut diagonal = row[0];
        row[0] = i + 1;
        for (j, cb) in b.iter().enumerate() {
            let above = row[j + 1];
            let cost = usize::from(ca != cb);
            row[j + 1] = (row[j] + 1).min(above + 1).min(diagonal + cost);
            diagonal = above;
        }
    }
    row[b.len()]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn distance_basics() {
        assert_eq!(edit_distance("kitten", "sitting"), 3);
        assert_eq!(edit_distance("same", "same"), 0);
        assert_eq!(edit_distance("", "abc"), 3);
    }

    #[test]
    fn suggests_close_names_only() {
        let names = ["cleanmeta", "sysinfo", "list", "doctor"];
        assert_eq!(closest("clenmeta", names.iter().copied()), vec!["cleanmeta"]);
        assert_eq!(closest("lsit", names.iter().copied()), vec!["list"]);
        assert!(closest("zzzzzz", names.iter().copied()).is_empty());
    }
}
