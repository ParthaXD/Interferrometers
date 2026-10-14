# Interference Simulator

An interactive Python simulator for exploring interference patterns in Fabry–Pérot and Michelson interferometers. It provides a simple way to see how changing optical parameters affects the intensity and shape of interference fringes.

## Features

- Switch between Fabry–Pérot and Michelson interferometers.
- Adjust wavelength, mirror separation, focal length, and refractive index.
- Change mirror reflectivity, fringe visibility, relative tilt, and phase.
- View live detector intensity patterns, radial intensity profiles, and horizontal cross-sections.
- Reset parameters to their default values.
- Export plots as PNG, PDF, or SVG files.

## Requirements

- Python 3
- NumPy
- Matplotlib
- Tkinter

Install the required Python libraries:

```bash
python -m pip install numpy matplotlib
```

On Fedora, install Tkinter if it is not already available:

```bash
sudo dnf install python3-tkinter
```

## Run the Simulator

Save the code as `main.py` and run:

```bash
python main.py
```

## Model

The Fabry–Pérot mode uses the Airy transmission formula for an ideal, symmetric, lossless cavity. The Michelson mode models two-beam interference with adjustable fringe visibility. The detector is modelled in the focal plane of a lens, and relative mirror tilt introduces a spatial variation in the optical path difference.

This is an educational scalar model intended to help visualize interference. It is not a full electromagnetic simulation or a complete model of a real interferometer such as LIGO.

## License

This project is available for educational and personal use.
