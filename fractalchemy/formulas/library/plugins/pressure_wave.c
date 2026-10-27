/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/pressure_wave_Plugin_by_timothy_vincent/pressure_wave.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin - pressure_wave
    Copyright 2010 timothy-vincent@deviantart.com
    
    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
*/

typedef struct
{
        double pressure_wave_x_freq, pressure_wave_y_freq;
    
} Variables;

// (SDK header apoplugin.h implied)

APO_PLUGIN("pressure_wave");

APO_VARIABLES(
        VAR_REAL(pressure_wave_x_freq, 1.0),
        VAR_REAL(pressure_wave_y_freq, 1.0)   
);


int PluginVarPrepare(Variation* vp)
{
    return TRUE; 
}


int PluginVarCalc(Variation* vp)
{
    FPx += VVAR*(FTx + (1/(VAR(pressure_wave_x_freq)*M_2PI))*sin(VAR(pressure_wave_x_freq)*M_2PI*FTx));
    FPy += VVAR*(FTy + (1/(VAR(pressure_wave_y_freq)*M_2PI))*sin(VAR(pressure_wave_y_freq)*M_2PI*FTy));

    return TRUE;
}
