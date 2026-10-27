/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/Tataz Utility Pack/Source/truchet_fill.c
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
        double tf_exponent;
        double tf_arc_width;
        double tf_seed;
        double exponent, onen, width, seed, seed2;
} Variables;

// (SDK header apoplugin.h implied)
//// (missing include apotest.h)

// Set the name of this plugin
APO_PLUGIN("Truchet_fill");

// Define the Variables
APO_VARIABLES(
VAR_REAL_CYCLE(tf_exponent, 0.001, 2.0, 2.0),
VAR_REAL_CYCLE(tf_arc_width, 0.001, 1.0, 0.5),
VAR_REAL(tf_seed, 0)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    VAR(exponent) = (VAR(tf_exponent) > 2.0 ? 2.0 : ( VAR(tf_exponent) < 0.001 ? 0.001 : VAR(tf_exponent)));
    VAR(onen) = 1.0 / VAR(exponent);
    VAR(width) = VAR(tf_arc_width) > 1.0 ? 1.0 : ( VAR(tf_arc_width) < 0.001 ? 0.001 : VAR(tf_arc_width));
    VAR(seed2) = sqrt(VAR(tf_seed) * 1.5) / (VAR(tf_seed) * 0.5) * 0.25;
    return TRUE; // Always return TRUE.
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
    double rmax = 0.5 * ( powf(2.0, VAR(onen)) -1.0) * VAR(width);
    double scale = 1.0 / VVAR;
    double modbase=65535.0;
    double multiplier=32747.0;//1103515245;
    double offset=12345.0;

    double x = FTx*scale;
    double y = FTy*scale;
    double intx = round(x);
    double inty = round(y);

    double r = x - intx;
      if (r < 0.0)
         x = 1.0+r;
      else
         x = r;

    r = y - inty;
      if (r < 0.0)
         y = 1.0+r;
      else
         y = r;

    double tiletype = 0.0;
    if (VAR(tf_seed) == 0.0)
    {
        tiletype = 0.0;
    }
    else
    {
        if (VAR(tf_seed) == 1.0)
            {
                tiletype = 1.0;
            }
        else {
                double xrand =FTx;
                double yrand =FTy;
             xrand = round(abs(xrand)) * VAR(seed2);
             yrand = round(abs(yrand)) * VAR(seed2);
            double niter = xrand + yrand + xrand*yrand;
            double randint = (VAR(tf_seed) + niter) * VAR(seed2) * 0.5;
            randint = fmod((randint * multiplier + offset), modbase);
            tiletype = fmod(randint, 2.0);
        }
    }

    double r0, r1;
        if (tiletype < 1.0) {  //Slow drawmode
           r0 = powf((powf(fabs(x), VAR(exponent)) + powf(fabs(y), VAR(exponent))), VAR(onen));
           r1 = powf((powf(fabs(x-1.0), VAR(exponent)) + powf(fabs(y-1.0), VAR(exponent))), VAR(onen));
        }
        else {
           r0 = powf((powf(fabs(x-1.0), VAR(exponent)) + powf(fabs(y), VAR(exponent))), VAR(onen));
           r1 = powf((powf(fabs(x), VAR(exponent)) + powf(fabs(y-1.0), VAR(exponent))), VAR(onen));
        }

    double x1, y1;
    double r00 = fabs(r0 - 0.5) / rmax;
       if (r00 < 1.0) {
            x1 = 2.0 *(x + floor(FTx));
            y1 = 2.0 *(y + floor(FTy));
       }
       else {
            x1 = 0.0;
            y1 = 0.0;
       }

    double r11 = fabs(r1 - 0.5) / rmax;
       if (r11 < 1.0) {
            FPx += x1 + 2.0 *(x + floor(FTx)) - FTx;
            FPy += y1 + 2.0*(y + floor(FTy)) - FTy;
       }
       else
       {
           FPx += x1 - FTx;
           FPy += y1 - FTy;
       }

    return TRUE;
}
