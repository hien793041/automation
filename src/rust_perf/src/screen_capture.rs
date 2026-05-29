use pyo3::prelude::*;

#[pyclass]
pub struct ScreenCapture;

#[pymethods]
impl ScreenCapture {
    #[new]
    fn new() -> Self {
        ScreenCapture
    }

    fn capture(&self) -> PyResult<Vec<u8>> {
        // TODO: fast screen capture implementation
        Ok(vec![])
    }
}
