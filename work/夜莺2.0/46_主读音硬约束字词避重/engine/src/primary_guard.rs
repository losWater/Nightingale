
use std::sync::OnceLock;
use crate::编码信息;
static INDICES: OnceLock<Option<Vec<usize>>> = OnceLock::new();
pub fn check(rows: &[编码信息]) -> bool {
    let ids = INDICES.get_or_init(|| {
        std::env::var("NIGHTINGALE_PRIMARY_GUARD").ok().map(|path| {
            let ids: Vec<usize> = serde_json::from_str(&std::fs::read_to_string(path).expect("read primary guard")).expect("parse primary guard");
            assert!(!ids.is_empty(), "empty primary guard");
            ids
        })
    });
    ids.as_ref().map_or(true, |ids| ids.iter().all(|&i| {
        let r = rows.get(i).expect("primary guard index out of bounds");
        r.词长 == 1 && first(r.全码.原始编码, r.全码.原始编码候选位置, r.简码.原始编码, r.简码.原始编码候选位置)
    }))
}
fn first(full: u64, fr: u8, short: u64, sr: u8) -> bool {
    (full != 0 && fr == 0) || (short != 0 && sr == 0)
}
#[cfg(test)]
mod tests {
    use super::first;
    #[test] fn either_first_is_enough() {
        assert!(first(123,0,12,1));
        assert!(first(123,1,12,0));
        assert!(first(123,0,0,0));
        assert!(!first(123,1,12,1));
        assert!(!first(0,0,0,0));
        assert!(!first(123,1,0,0));
    }
}
