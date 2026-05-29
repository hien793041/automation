use pyo3::prelude::*;

#[pyclass]
pub struct InputInjector;

#[pymethods]
impl InputInjector {
    #[new]
    fn new() -> Self {
        InputInjector
    }

    fn tap(&self, x: u32, y: u32) -> PyResult<()> {
        // TODO: low-latency input injection
        Ok(())
    }
}
