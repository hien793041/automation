use pyo3::prelude::*;

mod screen_capture;
mod image_buffer;
mod input_injector;

#[pymodule]
fn rokbot_perf(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<screen_capture::ScreenCapture>()?;
    m.add_class::<image_buffer::ImageBuffer>()?;
    m.add_class::<input_injector::InputInjector>()?;
    Ok(())
}
