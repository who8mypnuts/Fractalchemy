/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        holesq.cpp
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

// Apo Plugin by DarkBeam

#define APO_NOVARIABLES
// (missing include plugin.h)

// Set the name of this plugin
APO_PLUGIN("holesq");


// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
	// Always return TRUE.
	return TRUE;
}


// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
	double x = VVAR * FTx;
	double y = VVAR * FTy;
	double fax = fabs(x);
	double fay = fabs(y);
	
	if (fax + fay>1) { // use linear like loonie
			FPx += x;
			FPy += y;
		}
		else {
			double t;
			if (fax > fay) {
				t = (1 - fay)*( (x>0.0) ? 1.0 : -1.0 );
				t = (x + t)*.5;
				FPx += t;
				FPy += y;
			}
			else {
				t = (1 - fax)*( (y>0.0) ? 1.0 : -1.0);
				t = (y + t)*.5;
				FPx += x;
				FPy += t;
			}
		}

	// Add 3D compatibility
	FPz += VVAR * FTz;
	return TRUE;
}