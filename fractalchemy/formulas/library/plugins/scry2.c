/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        scry2.c
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
	int scry2_sides;
	double scry2_star;
	double scry2_circle;
	// ------------------------------
	double sina;
    double cosa;
	double sins;
    double coss;
	double sinc;
    double cosc;
	double VVAR_inv;

} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("scry2");

// Define the Variables
APO_VARIABLES(
    VAR_INTEGER_RANGE(scry2_sides, 1, 50, 4),
    VAR_REAL_RANGE(scry2_star, -1.0, 1.0, 0.0),
    VAR_REAL_RANGE(scry2_circle, -1.0, 1.0, 0.0)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
	VAR(VVAR_inv) = 1.0 / (VVAR + EPS);

    fsincos(M_2PI/VAR(scry2_sides), & VAR(sina), & VAR(cosa));
    fsincos(-M_PI_2*VAR(scry2_star), & VAR(sins), & VAR(coss));
    fsincos(M_PI_2*VAR(scry2_circle), & VAR(sinc), & VAR(cosc));

    return TRUE; // Always return TRUE.
}

int PluginVarCalc(Variation* vp)
{
    double xrt = FTx, yrt = FTy, swp;
    // r2 = xrt; // normal
    double r2 = xrt*VAR(coss) + fabs(yrt)*VAR(sins); // +star
    double r1 = 0.0;

    double circle = sqrt(sqr(xrt)+sqr(yrt));

    int i;

    for (i=0; i < VAR(scry2_sides)-1; i++) {
        // rotate around to get the the sides!!! :D
        swp = xrt * VAR(cosa) - yrt * VAR(sina);
        yrt = xrt * VAR(sina) + yrt * VAR(cosa);
        xrt = swp;

        // r2 = MAX(r2, xrt); // normal
        r2 = MAX(r2, xrt*VAR(coss) + fabs(yrt)*VAR(sins)); // +star
    }
    r2 = r2*VAR(cosc) + circle*VAR(sinc); // +circle
    r1 = r2;
    if (i > 1) {
          r2 = sqr(r2); // we want it squared, for the pretty effect
    } else {
          r2 = fabs(r2)*r2; // 2-faces effect JUST FOR i=1
    }

    double t = (r1*(r2 + VAR(VVAR_inv) ));
	double r = 1.0 / t;

	FPx += FTx * r;
	FPy += FTy * r;

    return TRUE;
}
