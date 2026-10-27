/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        bwrands.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

#define SGN(a) ((a) < 0 ? -1 : ((a) > 0 ? 1 : 0))   /* (was missing from the source) */
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

// bwraps7 - Bubble Wraps beta version

// Must define this structure before we include apoplugin.h
typedef struct
{
	double bwrands_cellsize;
	double bwrands_space;
	double bwrands_gain;
	double bwrands_inner_twist;
	double bwrands_outer_twist;
	int bwrands_seed;
	double bwrands_rrot;
	double bwrands_rmin;
	double bwrands_loonie_chance;
	double bwrands_petals_chance;
	int bwrands_minpetals;
	int bwrands_maxpetals;
    int petx;
    int pety;
    double g2;
    double g1;
	double r2;
	double rfactor;
} Variables;

// (SDK header apoplugin.h implied)
#define ABS2(a)    ((a) * SGN(a))

// Set the name of this plugin
APO_PLUGIN("bwrands");

// Define the Variables
APO_VARIABLES(
    VAR_REAL(bwrands_cellsize, 1.0),
    VAR_REAL(bwrands_space, 0.0),
    VAR_REAL(bwrands_gain, 1.25),
    VAR_REAL(bwrands_inner_twist, 0.0),
    VAR_REAL(bwrands_outer_twist, 0.0),
    VAR_INTEGER(bwrands_seed, 3210),
    VAR_REAL_CYCLE(bwrands_rrot, 0.0, 1.0, 1.0),
    VAR_REAL_CYCLE(bwrands_rmin, 0.0, 1.0, 0.25),
    VAR_REAL_CYCLE(bwrands_loonie_chance, 0.0, 1.0, 0.5),
    VAR_REAL_CYCLE(bwrands_petals_chance, 0.0, 1.0, 0.5),
    VAR_INTEGER_RANGE(bwrands_minpetals, 1, 1000, 3),
    VAR_INTEGER_RANGE(bwrands_maxpetals, 1, 1000, 20)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
	double radius = 0.5 * ( VAR(bwrands_cellsize) / ( 1.0 + VAR(bwrands_space) * VAR(bwrands_space) ) );
	
	// g2 is multiplier for radius
	VAR(g2) = sqr(VAR(bwrands_gain) ) / radius + 1.0e-6;
	
	// Start max_bubble as maximum x or y value before applying bubble
	double max_bubble = VAR(g2) * radius;
	
    if ( max_bubble > 2.0 )
    {
   	     // Values greater than 2.0 "recurve" round the back of the bubble
         max_bubble = 1.0;
    }
    else
    {
        // Expand smaller bubble to fill the space
	    max_bubble *= 1.0 / ( (max_bubble * max_bubble)/4.0 + 1.0);
    }

	VAR(r2) = radius * radius;
	VAR(rfactor) =  radius / max_bubble;
	
	VAR(petx) = MIN(
              VAR(bwrands_minpetals),
              VAR(bwrands_maxpetals));
	VAR(pety) = ABS2((
              VAR(bwrands_maxpetals) - 
              VAR(bwrands_minpetals) ));
    // if (VAR(pety) >= EPS) VAR(pety) += 1;
	
    return TRUE; // Always return TRUE.
}

inline int bytemix (int a, int b) {
    return ((a & 0x5A5A) ^ (b & 0xA5A5));
}

inline int bytexim (int a, int b) { // variation...
    return ((a & 0xAAAA) ^ (b & 0x5555));
}

inline int byteshf (int a, int b) {
    return ((a << 8) ^ (b >> 8) ) & 0xFFFF;
}

inline int bytezhf (int a, int b) { // variation...
    return ((a << 6) ^ (b >> 6)) & 0xFFFF;
}

inline int byteprimes (int a, int b) { // variation...
    return ((a * 857 - 4) & 0xFF00 ^ (-b * 977 + 8) & 0x00FF ) ;
}

inline int bytehey (int a, int b) { // *unused* advanced variation...
    int a0 = a & 0x000F;
    //int a1 = (a & 0x00F0) >>4;
    int a2 = (a & 0x0F00) >>8;
    //int a3 = (a & 0xF000) >>12;
    //int b0 = b & 0x000F;
    int b1 = (b & 0x00F0) >>4;
    //int b2 = (b & 0x0F00) >>8;
    int b3 = (b & 0xF000) >>12;
    return ( (a0 << 12) ^ (b1 << 8) ^ (a2 << 4) ^ (b3) ) & 0xFFFF;
}

void sort_ (double* a, double* b) {
    double tmp = MIN(*a,*b);
    *b = MAX(*a,*b);
    *a = tmp;
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
    double Vx, Vy; // V is "global" vector,
	int Ix, Iy, xx, yy, xy, tt; // int part x,y
	double Ssz, Aan; 
	double LoonieChance = -1.0, PetalsChance = -1.0; 
	double NPetals = 0.333333; 
	double Cx, Cy; // C is "cell centre" vector
	double Lx, Ly; // L is "local" bubble vector
	double r, theta, s, c;
	double Vv2,flwr;
    	
    Vx = FTx;
    Vy = FTy;

	if ( VAR(bwrands_cellsize) == 0.0 )
	{
		// Linear if cells are too small
		FPx += VVAR * Vx;
		FPy += VVAR * Vy;
		return TRUE;
	}

	Ix = floor( Vx / VAR(bwrands_cellsize) );
	Iy = floor( Vy / VAR(bwrands_cellsize) );
	
	Cx = ( Ix + 0.5 ) * VAR(bwrands_cellsize);
	Cy = ( Iy + 0.5 ) * VAR(bwrands_cellsize);
	
    // mess with Ix & Iy to get random
	xx = Ix ^ 0xB641;
	yy = Iy ^ 0x9D81;
	xy = xx * yy + VAR(bwrands_seed);
	xx &= 0xFFFF; yy &= 0xFFFF; xy &= 0xFFFF;
	// no less than 3 remixes are needed to get good randomness
	// use always identical mixes or you lose some data (you don't want this!)
    tt = bytemix (xx,yy);
    yy = bytemix (yy,xx);
    xx = tt;
    tt = byteshf (xx,xy);
    yy = byteshf (xy,yy);
    xx = tt;
    tt = bytexim (xx,yy);
    yy = bytexim (yy,xx);
    xx = tt;
    Ssz = ((double) xx) / 65535.0; // to get a range not 0-1 for circles size edit here
    Ssz = VAR(bwrands_rmin)+ Ssz*(1.0-VAR(bwrands_rmin));
    Aan = VAR(bwrands_rrot) * M_2PI * ((double) yy) / 65535.0; // to get a range not 0-2pi for rotations size edit here
    tt = byteprimes (xx,yy);
    yy = byteprimes (yy,xx);
    xx = tt;
    LoonieChance = -((double) xx) / 65535.0 + VAR(bwrands_loonie_chance); // 0.5 for a chance 50% !
    if (LoonieChance < 0) PetalsChance =  LoonieChance + VAR(bwrands_petals_chance);
    // user choice but don't upset modulus...
    if (VAR(pety) == 0) NPetals = (double) VAR(petx); // ... when min = max
    else NPetals = (double) (VAR(petx) + (yy >> 3) % (1+VAR(pety))); // yy last byte is not enough random. But yy >> 3 is good
    
    if ( LoonieChance <= PetalsChance ) LoonieChance = -1.0; // the bigger probability must win.
    
    // if more random values are needed remix again :D
    
	Lx = Vx - Cx;
	Ly = Vy - Cy;
	
    Vv2 = Ssz * VAR(r2);
    
	if ( ( Lx * Lx + Ly * Ly ) >  Vv2 )
	{
		// Linear if outside the bubble
		FPx += VVAR * Vx;
		FPy += VVAR * Vy;
		return TRUE;
	}
	
	if ( LoonieChance > 0.0 )
	{
    	// We're in the loonie!
    	// r =  Vv2 / (Lx * Lx + Ly * Ly) - MAX(MIN(VAR(bwrands_gain),1.0),0.0); LOOKING BAD!!!
    	r =  Vv2 / (Lx * Lx + Ly * Ly) - 1.0;
    	r =  sqrt( r );
    	Lx *= r ;
    	Ly *= r ;
    	Vv2 = 1.0; // recycled var
	}
	else if ( PetalsChance > 0.0 )
	{
    	// We're in the petals!
    	flwr = NPetals / M_2PI*(M_PI+atan2(Ly,Lx));
    	flwr = flwr - (int)(flwr);
    	flwr = fabs( flwr-0.5 ) * 2.0;
    	r =  sqrt(Lx * Lx + Ly * Ly);
    	
    	// We need a little chaos game to fill the empty space outside the flower.
    	PetalsChance = random01();
    	
    	if (PetalsChance < .5*(flwr+.5))
    	{
            // petals
        	Lx *= (1.0-r)*(flwr*1.1) ; // 1.1 remove the ugly border
        	Ly *= (1.0-r)*(flwr*1.1) ; // 1.1 remove the ugly border
        }
    	else
    	{ 
            Vv2 = sqrt(Vv2); // dist to circle border
            // filling the rest of the circle
        	Lx *= (Vv2-r*(1.0-flwr))/(r + EPS) ;
        	Ly *= (Vv2-r*(1.0-flwr))/(r + EPS)  ;
        }
        
    	Vv2 = 1.0; // recycled var
	}
	else
	{
    	// We're in the bubble!
    	// Bubble distortion on local co-ordinates:
    	Lx *= VAR(g2);
    	Ly *= VAR(g2);
    	r =  VAR(rfactor) / ( (Lx * Lx + Ly * Ly)/(4.0*Ssz) + 1.0);
    	Lx *= r ;
    	Ly *= r ;
    	Vv2 = sqrt(Ssz); // recycled var
	}
 	// Spin around the centre:
    r =  Vv2 * (Lx * Lx + Ly * Ly) / VAR(r2);  // r should be 0.0 - 1.0
    theta = VAR(bwrands_inner_twist) * ( 1.0 - r ) + VAR(bwrands_outer_twist) * r;
    fsincos( theta + Aan , &s, &c );
    
    // Add rotated local vectors direct to centre (avoids use of temp storage)
    Vx = Cx    + c * Lx + s * Ly;
    Vy = Cy    - s * Lx + c * Ly;
   	
	// Finally add values in
	FPx += VVAR * Vx;
	FPy += VVAR * Vy;
	
	return TRUE;
}
