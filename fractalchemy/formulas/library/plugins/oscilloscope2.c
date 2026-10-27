/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        oscilloscope2.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
*/

// Must define this structure before we include apoplugin.h
typedef struct
{
    double osco2_separation;
    double osco2_frequencyx;
    double osco2_frequencyy;
    double osco2_amplitude;
    double osco2_perturbation;
    double osco2_damping;
    // --------------------------
    double _tpf,_tpf2;
    int _noDamping;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("oscilloscope2");

// Define the Variables
APO_VARIABLES(
    VAR_REAL(osco2_separation, 1.0),
    VAR_REAL(osco2_frequencyx, 1.0),
    VAR_REAL(osco2_frequencyy, 0.333),
    VAR_REAL(osco2_amplitude, 1.0),
    VAR_REAL(osco2_perturbation, 1.0),
    VAR_REAL(osco2_damping, 0.0)
);


int PluginVarPrepare(Variation* vp)
{
    VAR(_tpf) = M_2PI * VAR(osco2_frequencyx);
    VAR(_tpf2) = M_2PI * VAR(osco2_frequencyy);
    VAR(_noDamping) = fabs(VAR(osco2_damping)) <= EPS;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t;
    double pt = VAR(osco2_perturbation) * sin(VAR(_tpf2) * FTy);
    if (VAR(_noDamping)) {
      t = VAR(osco2_amplitude) * (cos(VAR(_tpf) * FTx + pt)) + VAR(osco2_separation);
    }
    else {
      t = VAR(osco2_amplitude) * exp(-fabs(FTx) * VAR(osco2_damping)) * (cos(VAR(_tpf) * FTx + pt)) + VAR(osco2_separation);
    }

    if(fabs(FTy) <= t)
    {
       FPx -= VVAR*FTx;
       FPy -= VVAR*FTy;
    }
    else
    {
       FPx += VVAR*FTx;
       FPy += VVAR*FTy;
    }
    return TRUE;
}

