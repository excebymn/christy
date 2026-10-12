//! Signal setup done once at startup.

/// Rust ignores SIGPIPE by default. That makes `println!` panic on
/// `christy list | head`, and, because an ignored signal stays ignored across
/// `exec`, it would also leak into every tool the core launches. Restoring the
/// default gives normal Unix behavior: the process just ends quietly.
pub fn restore_sigpipe() {
    #[cfg(unix)]
    {
        const SIGPIPE: i32 = 13;
        const SIG_DFL: usize = 0;
        extern "C" {
            fn signal(signum: i32, handler: usize) -> usize;
        }
        // SAFETY: `signal` is the libc function of that name; SIGPIPE and
        // SIG_DFL have the same values on Linux and macOS. Called once,
        // before any other thread exists.
        unsafe {
            signal(SIGPIPE, SIG_DFL);
        }
    }
}
