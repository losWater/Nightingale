use rand::{Rng, RngCore, SeedableRng};
use rand::rngs::StdRng;
use std::cell::RefCell;
thread_local! { static STATE: RefCell<StdRng> = RefCell::new(StdRng::seed_from_u64(std::env::var("NIGHTINGALE_TRIAL_SEED").expect("trial seed required").parse().expect("integer seed"))); }
pub struct Handle;
impl RngCore for Handle {
 fn next_u32(&mut self)->u32 { STATE.with(|s|s.borrow_mut().next_u32()) }
 fn next_u64(&mut self)->u64 { STATE.with(|s|s.borrow_mut().next_u64()) }
 fn fill_bytes(&mut self,dst:&mut [u8]) { STATE.with(|s|s.borrow_mut().fill_bytes(dst)) }
}
pub fn rng()->Handle { Handle }
pub fn random_f64()->f64 { rng().random::<f64>() }
pub fn random_range(range:std::ops::Range<usize>)->usize { rng().random_range(range) }
