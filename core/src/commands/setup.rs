//! `christy setup [tool]`.
//!
//! With a name: runs that tool's setup script, always (handy to repair or
//! refresh an environment). Without: sets up every tool that currently needs
//! it. Typing the command is the consent, so there's no extra prompt.

use super::find_valid_tool;
use crate::deps;
use crate::error::CoreError;
use crate::manifest::Manifest;
use crate::messages as msg;
use crate::paths::Paths;
use crate::registry::{self, Registry};
use crate::runtime;
use crate::setup;

pub fn run(name: Option<&str>) -> Result<i32, CoreError> {
    let paths = Paths::resolve()?;
    let registry = registry::load_or_build(&paths)?;

    match name {
        Some(name) => {
            let manifest = find_valid_tool(&registry, name)?;
            runtime::check_platform(manifest)?;
            setup::run_and_verify(&paths, manifest)?;
            Ok(0)
        }
        None => setup_all(&paths, &registry),
    }
}

fn setup_all(paths: &Paths, registry: &Registry) -> Result<i32, CoreError> {
    let mut with_script: Vec<&Manifest> = Vec::new();
    let mut by_hand = Vec::new();

    for manifest in registry.valid_tools() {
        if runtime::check_platform(manifest).is_err() {
            continue;
        }
        let missing = deps::check(paths, manifest);
        if missing.is_empty() {
            continue;
        }
        if manifest.setup.is_some() {
            with_script.push(manifest);
        } else {
            by_hand.push((manifest, missing));
        }
    }

    if with_script.is_empty() && by_hand.is_empty() {
        println!("{}", msg::SETUP_NOTHING_TO_DO);
        return Ok(0);
    }

    let mut done = 0;
    let mut failed = 0;
    for manifest in &with_script {
        match setup::run_and_verify(paths, manifest) {
            Ok(()) => done += 1,
            Err(err) => {
                err.report();
                failed += 1;
            }
        }
    }
    for (manifest, missing) in &by_hand {
        eprintln!("{}", msg::setup_manual(&manifest.name, missing));
    }

    println!("{}", msg::setup_summary(done, failed, by_hand.len()));
    Ok(if failed > 0 || !by_hand.is_empty() { 1 } else { 0 })
}
