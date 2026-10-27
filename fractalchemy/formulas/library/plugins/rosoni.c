/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        rosoni.c
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
    int rosoni_maxiter;
    int rosoni_sweetiter;
    int rosoni_altshapes;
    double rosoni_cutoff;
    double rosoni_radius;
    double rosoni_dx;
    double rosoni_dy;
    // ------------------------
    double _sina, _cosa;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("rosoni");

// Define the Variables
APO_VARIABLES(
    VAR_INTEGER_RANGE(rosoni_maxiter, 1, 1024, 25),
    VAR_INTEGER_RANGE(rosoni_sweetiter, 0, 1023, 3),
    VAR_INTEGER_RANGE(rosoni_altshapes, 0, 1, 0),
    VAR_REAL(rosoni_cutoff, 1.0),
    VAR_REAL(rosoni_radius, 0.4),
    VAR_REAL(rosoni_dx, 0.6),
    VAR_REAL(rosoni_dy, 0.0)
);


int PluginVarPrepare(Variation* vp)
{
    double phi = M_2PI / (double) VAR(rosoni_maxiter);
    VAR(_sina) = sin(phi);
    VAR(_cosa) = cos(phi);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
   double x = FTx;
    double y = FTy;
    double r = sqrt(sqr(x) + sqr(y)) - VAR(rosoni_cutoff);
    if (VAR(rosoni_cutoff) < 0.0)
      r = MAX(fabs(x), fabs(y)) + VAR(rosoni_cutoff);
    int cerc = r > 0.0;

    if (cerc) {
      FPx += VVAR * x;
      FPy += VVAR * y;
      return TRUE;
    }

    cerc = (VAR(rosoni_dx) > 0.0);
    int i;
    double xrt = x, yrt = y, swp, r2 = xrt;
    double sweetx = xrt, sweety = yrt;

    for (i = 0; i < VAR(rosoni_maxiter); i++) {
      if (VAR(rosoni_altshapes) == 0) {
        r2 = sqr(xrt - VAR(rosoni_dx)) + sqr(yrt - VAR(rosoni_dy)) - sqr(VAR(rosoni_radius)); // circle
        if (VAR(rosoni_radius) < 0.0)
          r2 = MAX(fabs(xrt - VAR(rosoni_dx)), fabs(y - VAR(rosoni_dy))) + VAR(rosoni_radius); // square
      }
      else {
        r2 = ((xrt - VAR(rosoni_dx)) < 0.0) ? -(xrt - VAR(rosoni_dx)) : ((sqr(yrt - VAR(rosoni_dy))) - sqr(xrt - VAR(rosoni_dx)) * (sqr(VAR(rosoni_radius)) - sqr(xrt - VAR(rosoni_dx)))); // lemniscate
        if (VAR(rosoni_radius) < 0.0)
          r2 = fabs(atan2(y - VAR(rosoni_dy), xrt - VAR(rosoni_dx))) * M_1_PI + VAR(rosoni_radius); // angle
      }
      cerc ^= (r2 <= 0.0);
      // rotate around to get the the sides!!! :D
      if (i == VAR(rosoni_sweetiter)) {
        sweetx = xrt;
        sweety = yrt;
      }
      swp = xrt * VAR(_cosa) - yrt * VAR(_sina);
      yrt = xrt * VAR(_sina) + yrt * VAR(_cosa);
      xrt = swp;
    }

    if (cerc) {
      if (VAR(rosoni_sweetiter) == 0) {
        if (VAR(rosoni_dy) != 0)
          FPx -= VVAR * sweetx;
        else
          FPx += VVAR * sweetx;
        FPy -= VVAR * sweety;
      }
      else
      {
        FPx += VVAR * sweetx;
        FPy += VVAR * sweety;
      }
      return TRUE;
    }
    FPx += VVAR * x;
    FPy += VVAR * y;
    return TRUE;
}

