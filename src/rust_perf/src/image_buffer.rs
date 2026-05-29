use pyo3::prelude::*;

#[pyclass]
pub struct ImageBuffer {
    data: Vec<u8>,
}

#[pymethods]
impl ImageBuffer {
    #[new]
    fn new(width: usize, height: usize) -> Self {
        ImageBuffer {
            data: vec![0u8; width * height * 4],
        }
    }

    fn as_bytes(&self) -> Vec<u8> {
        self.data.clone()
    }
}
