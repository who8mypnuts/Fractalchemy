/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        spligon.cpp
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

typedef struct
{
	double spligon_sides;
	double spligon_r;
	double spligon_i;
	double j;
	double th;
	double thi;

} Variables;

// (missing include plugin.h)

// Set the name of this plugin
APO_PLUGIN("spligon");

APO_VARIABLES(
	VAR_REAL_RANGE(spligon_sides, 1e-5, 1e5, 3.0),
	VAR_REAL(spligon_r, 1),
	VAR_REAL(spligon_i, 1)
	);


// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
	VAR(th) = VAR(spligon_sides) * M_1_2PI;
	VAR(thi) = 1.0 / VAR(th);
	VAR(j) = 3.14159265358979323846 * VAR(spligon_i) / (-2.0 * VAR(spligon_sides)) ;
	// Always return TRUE.
	return TRUE;
}


// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
	double dx,dy;
	double t = VAR(thi) * floor(atan2(FTy, FTx)*VAR(th)) + VAR(j);
	fsincos(t, &dx, &dy);
	FPx += VVAR * (FTx + dy * VAR(spligon_r));
	FPy += VVAR * (FTy + dx * VAR(spligon_r));

	// Add 3D compatibility
	FPz += VVAR * FTz;
	return TRUE;
}