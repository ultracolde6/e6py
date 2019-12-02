import numpy as np
import xarray as xr
import scipy.constants as const
from functools import reduce
from . import E6utils


class Atom:
    """Data container for atom"""
    def __init__(self, element):
        if element == 'Rb87':
            self.isboson = True
            self.gammaD1 = 1 / 27.679e-9
            self.transitionfrequencyD1 = 377.107463380e12  # Center transition frequency D1 line (Steck)
            self.IsatD1 = 4.4876 * 1e-3 * (1e2 ** 2)  # Far-Detuned, pi-polarized, W/m^2
            self.gammaD2 = 1 / 26.2348e-9
            self.transitionfrequencyD2 = 384.2304844685e12  # Center transition frequency of D2 line (Steck)
            self.IsatD2 = 2.50399 * 1e-3 * (1e2 ** 2)  # Far-Detuned, pi-polarized, W/m^2
            self.gamma = 0.5 * (self.gammaD1 + self.gammaD2)  # Decay from 5P state (Steck)
            self.transitionfrequency = 0.5 * (
                    self.transitionfrequencyD1 + self.transitionfrequencyD2)  # Arbitrary! Check
            self.finestructure_splitting = self.transitionfrequencyD2 - self.transitionfrequencyD1
            self.nuclearspin = 1.5
            self.spin = 0.5
            self.gj = 2.00233113  # Value from Steck
            self.mass = 1.443160648e-25  # Value from Steck
            self.scattering_length = 100.4 * const.value('Bohr radius')
        else:
            print('Element not defined. Using Rubidium-87')
            self.isboson = True
            self.gammaD1 = 1 / 27.7e-9
            self.transitionfrequencyD1 = 377.1074635e12  # Center transition frequency D1 line (Steck)
            self.IsatD1 = 4.4876 * 1e-3 * (1e2 ** 2)  # Far-Detuned, pi-polarized, W/m^2
            self.gammaD2 = 1 / 26.24e-9
            self.transitionfrequencyD2 = 384.2304844685e12  # Center transition frequency of D2 line (Steck)
            self.IsatD2 = 2.50399 * 1e-3 * (1e2 ** 2)  # Far-Detuned, pi-polarized, W/m^2
            self.gamma = 0.5 * (self.gammaD1 + self.gammaD2)  # Decay from 5P state (Steck)
            self.transitionfrequency = 0.5 * (
                    self.transitionfrequencyD1 + self.transitionfrequencyD2)  # Arbitrary! Check
            self.finestructure_splitting = self.transitionfrequencyD2 - self.transitionfrequencyD1
            self.nuclearspin = 1.5
            self.spin = 0.5
            self.gj = 2.00233113  # Value from Steck
            self.mass = 1.443160648e-25  # Value from Steck
            self.scattering_length = 100.4 * const.value('Bohr radius')

    def optical_potential(self, I, wavelength=None, f_field=None):
        # Convert an optical intensity into an optical potential
        if f_field is None:
            try:
                f_field = const.c / wavelength
            except TypeError:
                print('Must provide wavelength if frequency is not specified')
        f0_D1 = self.transitionfrequencyD1
        f0_D2 = self.transitionfrequencyD2
        U_rotating = (const.hbar * I / 8) * \
                     (
                             (self.gammaD1 ** 2 / (2 * np.pi * (f_field - f0_D1) * self.IsatD1))
                             + (self.gammaD2 ** 2 / (2 * np.pi * (f_field - f0_D2) * self.IsatD2))
                     )
        U_counterrotating = (const.hbar * I / 8) * \
                            (
                                    (self.gammaD1 ** 2 / (2 * np.pi * (f_field + f0_D1) * self.IsatD1))
                                    + (self.gammaD2 ** 2 / (2 * np.pi * (f_field + f0_D2) * self.IsatD2))
                            )
        return U_rotating + U_counterrotating


class Beam:
    # Class to model an optical gaussian beam
    def __init__(self, waist_x, power, wavelength, waist_y=None, z0_x=0, z0_y=0):
        self.waist_x = waist_x
        if waist_y is None:
            waist_y = waist_x
        self.waist_y = waist_y
        self.power = power
        self.I0 = 2 * power / (np.pi * waist_x * waist_y)
        self.wavelength = wavelength
        self.z0_x = z0_x
        self.z0_y = z0_y
        self.zr_x = np.pi * waist_x ** 2 / wavelength
        self.zr_y = np.pi * waist_y ** 2 / wavelength
        self.trans_list = []
        # self.trans_list is a list of transformations (translations and rotations)
        # to apply to beam geometry. List of functions which takes 3d vectors as inputs and output 3d vectors
        self.field = None

    def beam_intensity_profile(self, x, y, z):
        # Gaussian intensity function. Electric field functionality not implemented
        [x, y, z] = reduce(lambda vec, f: f(vec), self.trans_list[::-1], [x, y, z])
        I0 = self.power_to_max_intensity(self.power, self.waist_x, self.waist_y)
        return self.gaussian_beam_profile(x, y, z,
                                          I0=I0, wavelength=self.wavelength,
                                          w0_x=self.waist_x, w0_y=self.waist_y,
                                          z0_x=self.z0_x, z0_y=self.z0_y)

    def make_field(self, x0=(-1, -1, -1), xf=(1, 1, 1), n_steps=(10, 10, 10)):
        # Make xarray of the optical intensity
        self.field = E6utils.func3d_xr(self.beam_intensity_profile, x0, xf, n_steps)
        return self.field

    def translate(self, trans_vec):
        # Add translation transformation to self.trans_list
        self.trans_list.append(lambda v: E6utils.translate_vec(v, -trans_vec))
        return

    def transform(self, trans_mat):
        # Add matrix transformation to self.trans_list
        self.trans_list.append(lambda v: E6utils.transform_vec(v, trans_mat))

    def rotate(self, axis=(1, 0, 0), angle=0):
        # Add rotation transformation to self.trans_list
        rot_mat = E6utils.rot_mat(axis, -angle)
        self.transform(rot_mat)
        return

    @staticmethod
    def waist_profile(waist, wavelength, z):
        return waist * np.sqrt(1 + (z / Beam.w0_to_zr(waist, wavelength)) ** 2)

    @staticmethod
    def w0_to_zr(w0, wavelength):
        return np.pi * w0 ** 2 / wavelength

    @staticmethod
    def power_to_max_intensity(P, w0_x, w0_y=None):
        if w0_y is None:
            w0_y = w0_x
        return 2 * P / (np.pi * w0_x * w0_y)

    @staticmethod
    def gaussian_beam_profile(x, y, z, I0, w0_x, z0_x, wavelength, w0_y=None, z0_y=None):
        if w0_y is None:
            w0_y = w0_x
        if z0_y is None:
            z0_y = z0_x
        return I0 * ((w0_x / Beam.waist_profile(w0_x, wavelength, z - z0_x))
                     * (w0_y / Beam.waist_profile(w0_y, wavelength, z - z0_y))
                     * E6utils.gaussian_2d(x, y, x0=0, y0=0, sx=w0_x/2, sy=w0_y/2))  # Note that sx=w0_x/2


class OptTrap:
    def __init__(self, beams, atom=Atom('Rb87'), quiet=False):
        try:
            len(beams)
        except TypeError:
            beams = (beams,)
        self.beams = beams
        self.atom = atom
        self.trap_freqs = [0, 0, 0]
        self.trap_freq_gmean = 0
        self.trap_depth = 0
        self.pot_field = None
        self.get_trap_params()
        self.quiet = quiet
        if not self.quiet:
            print('Created optical trap with the following properties:')
            self.print_properties()

    def get_trap_params(self):
        tot_pot_field = self.make_pot_field(x0=(-1e-6,) * 3, xf=(1e-6,) * 3, n_steps=(10,) * 3)
        hess = E6utils.hessian(tot_pot_field, x0=0, y0=0, z0=0)
        vals = np.linalg.eig(hess)[0]  # [0] makes it only return eigenvalues and not eigenvectors
        self.trap_freqs = np.sqrt(vals / self.atom.mass)
        self.trap_freq_gmean = np.prod(self.trap_freqs) ** (1 / 3)
        self.trap_depth = -tot_pot_field.max().values
        return self.trap_depth, self.trap_freqs

    def make_pot_field(self, x0=(-1e-6,) * 3, xf=(1e-6,) * 3, n_steps=(10,) * 3):
        x0 = E6utils.single_to_triple(x0)
        xf = E6utils.single_to_triple(xf)
        n_steps = E6utils.single_to_triple(n_steps)
        beam = self.beams[0]
        tot_pot_field = beam.make_field(x0, xf, n_steps)
        tot_pot_field = tot_pot_field.pipe(lambda x: self.atom.optical_potential(x, beam.wavelength))
        for i in range(1, len(self.beams)):
            beam = self.beams[i]
            beam_opt_field = beam.make_field(x0, xf, n_steps)
            beam_pot_field = beam_opt_field.pipe(lambda x: self.atom.optical_potential(x, beam.wavelength))
            tot_pot_field = tot_pot_field + beam_pot_field
        self.pot_field = tot_pot_field
        return self.pot_field

    def calc_psd(self, N, T, quiet=None):
        if quiet is None:
            quiet = self.quiet
        psd = N * ((const.hbar * self.trap_freq_gmean) / (const.k * T)) ** 3
        if not quiet:
            print(f'PSD = {psd:.1e}')
        return psd

    def calc_peak_density(self, N, T, quiet=None):
        if quiet is None:
            quiet = self.quiet
        lambda_db = const.h / np.sqrt(2 * np.pi * self.atom.mass * const.k * T)
        n0 = self.calc_psd(N, T, quiet=True) / (lambda_db ** 3)
        if not quiet:
            print(f'Peak Density = {n0*(1e-2 ** 3):.1e} cm^-3')
        return n0

    def print_properties(self):
        print(f'Trap Depth = {(self.trap_depth/const.h)*1e-6:.2f} MHz = {(self.trap_depth/const.k)*1e6:.2f} \\mu K')
        print('Trap Frequencies = \n'
              + '\n'.join([f'{self.trap_freqs[i]/(2*np.pi):.2f} Hz' for i in range(3)])
              )
        print(f'Geometric Mean = {self.trap_freq_gmean/(2*np.pi):.2f} Hz')
        return


def make_grav_pot(mass=Atom('Rb87').mass, grav_vec=(0, 0, -1),
                  x0=(-1,)*3, xf=(1,)*3, n_steps=(10,)*3):
    def grav_func(x, y, z):
        grav_comp = np.dot([x, y, z], grav_vec)
        return -mass*const.g*grav_comp
    grav_pot = E6utils.func3d_xr(grav_func, x0, xf, n_steps)
    return grav_pot


def make_sphere_quad_pot(gf=-(1/2), mf=-1, B_grad=1, units='T/m', trans_list=[],
                         strong_axis=(0, 0, 1),
                         x0=(-1,)*3, xf=(1,)*3, n_steps=(10,)*3):
    if units == 'T/m':
        pass
    elif units == 'G/cm':
        B_grad = B_grad*1e-4*1e2  # Convert G/cm into T/m
    else:
        print('unrecognized units, only T/m and G/cm supported')
    gyromagnetic_ratio_classical = 2*np.pi*1.4*1e6*1e4
    # Convert 1.4 MHz/Gauss into 1.4e10 Hz/T
    mat = E6utils.matrix_rot_v_onto_w((0, 0, 1), strong_axis)
    if not (np.array([strong_axis]) == np.array([0, 0, 1])).all():
        trans_list = [lambda vec: E6utils.transform_vec(vec, mat)] + trans_list

    def sphere_quad_func(x, y, z):
        if trans_list != []:
            [x, y, z] = reduce(lambda vec, f: f(vec), trans_list[::-1], [x, y, z])
        return gf * mf * gyromagnetic_ratio_classical * const.hbar\
                  * np.sqrt((0.5*B_grad*x)**2 + (0.5*B_grad*y)**2 + (B_grad*z)**2)
    sphere_quad_pot = E6utils.func3d_xr(sphere_quad_func, x0, xf, n_steps)
    return sphere_quad_pot
