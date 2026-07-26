KPL/FK

   Topocentric Reference Frame Definition Kernel for DSN Stations
   =====================================================================

   Original file name:                   earth_topo_260717.tf
   Creation date:                        2026 July 17 01:15
   Created by:                           Nat Bachman  (NAIF/JPL)


   Introduction
   =====================================================================

   This file defines topocentric reference frames associated with each
   of the DSN stations cited in the list below under "Position Data."
   Each topocentric reference frame ("frame" for short) is centered at
   the associated station and is fixed to the earth. Mathematically, a
   frame "definition" is a specification of the orientation of the
   frame relative to another frame. In this file, the other frame,
   which we'll refer to as the "base frame," is the terrestrial
   reference frame ITRF93.

   The orientation of a topocentric frame relative to the base frame
   relies on a reference spheroid (see "Data Sources" below). The
   z-axis of the topocentric frame contains the station location and is
   normal to the reference spheroid:  the line containing the z-axis
   intersects the reference spheroid at right angles. The x-axis
   points north and the y-axis points west.  Note that stations
   normally have non-zero altitude with respect to the spheroid.

   Loosely speaking, a topocentric frame enables computations involving
   the local directions "north", "west," and "up" at a surface point on
   an extended body. For example, the "elevation" of an object relative
   to the center of a topocentric frame is the object's latitude in
   that frame. The corresponding azimuth is the angle from the
   topocentric frame's x-axis to the projection of the center-to-object
   vector onto the topocentric frame's x-y plane, measured in the
   clockwise direction.

   The orientation of a topocentric frame relative to the base frame can
   be described by an Euler angle sequence.  Let M be the rotation
   matrix that maps vectors from the base frame to a specified
   topocentric frame.  Then


      M   =  [ Pi  ]  [ Pi/2 - LAT ]  [ LON ]
                    3               2        3

   where LON, LAT are the associated station's geodetic latitude and
   longitude.  Note that the frame definitions below actually
   provide Euler angles for the inverse of M and use units of
   degrees, so the angle sequences are

       -1                         o          o
      M   =  [ -LON ]   [ LAT - 90 ]    [ 180 ]
                     3               2         3

   See the Rotation Required Reading for details concerning Euler angles.


   Regarding the structure of this file
   ------------------------------------

   The SPICE utility PINPOINT was used to create the topocentric frame
   specifications contained in this file. The comment file

      earthstns_fx_260717.cmt

   was used as an input to the PINPOINT run, and that file is automatically
   included by PINPOINT in the frame kernel it creates.


   Using this kernel
   =====================================================================

   Revision description
   --------------------

   This kernel is based on data from a single, current source: [1].

   This kernel supersedes the kernel

      earth_topo_201023.tf

   The set of stations covered by this file has changed from that file as
   follows:
 
      Deleted stations (not present in current file):

         None.

      Added stations:

         DSS-23
         DSS-33
   
      Changed data: 

         DSS-53


   Planned updates
   ---------------
 
   Updates will be be made to keep this file in sync with updates to the
   source document [1]. 


   Using this kernel
   =====================================================================

   Kernel loading
   --------------

   In order for a SPICE-based program to make use of this kernel, the
   kernel must be loaded via the SPICE routine FURNSH. If you are
   running application software created by a third party, see the
   documentation for that software for instructions on kernel
   management.

   See also "Associated frame kernels" and "Associated PCK files" below.
 

   Associated PCK files
   --------------------

   For high-accuracy work, this kernel should be used together with a
   high-precision, binary earth PCK file.

      NAIF produces these kernels on a regular basis; they can be
      obtained via anonymous ftp from the NAIF server

         naif.jpl.nasa.gov

      or downloaded from the URL

         https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/

      The PCK is located in the path

         pub/naif/generic_kernels/pck

      The file name is of the form

         earth_000101_yymmdd_yymmdd.bpc

      The first two dates are the file's start and stop times; the third
      is the epoch of the last datum in the EOP file: data from
      this epoch forward are predicted.

      The file's coverage starts at a fixed date (currently chosen to
      be 2000 Jan. 1) and extends to the end of the predict region,
      which has a duration of roughly 3 months.

      The same location contains a file with identical contents and a fixed
      name:

         earth_latest_high_prec.bpc

      This file may be convenient for automated downloads.

      NAIF also provides a low-accuracy, long-term predict binary Earth PCK.
      See the file

          aareadme.txt

      in the location cited above for details.

   Associated SPK files
   --------------------

   This file is compatible with the SPK files

       earthstns_fx_260717.bsp       [reference frame: EARTH_FIXED]
       earthstns_itrf93_260717.bsp   [reference frame: ITRF93     ]

   both of which provide state vectors for each station covered by this file.

   Most applications will need to load one of the above SPK files in order to
   make use of this frame kernel.


   Data sources
   =====================================================================

   All data presented here are from reference [1].


   Reference Spheroid
   ------------------

   The reference bi-axial spheroid is defined by an equatorial and a
   polar radius. Calling these Re and Rp respectively, the flattening
   factor f is defined as

      f = ( Re - Rp ) / Re

   For the reference spheroid used by this file, the equatorial radius
   Re and inverse flattening factor 1/f are

      Re  = 6378137 m
      1/f = 298.2572236

   These parameters may be used to convert station locations at the epoch
   2003 JAN 01 TDB to geodetic coordinates matching those given in [1].

   The reference spheroid is used for derivation of the topocentric frame
   orientation Euler angles used in this file.

   The PCK file listed as a PINPOINT input below defines Earth radii
   consistent with these parameters. This PCK is not provided by NAIF, but
   the PCK may be created from the following text by prefixing a backslash
   character to the

       begindata
       begintext

   strings in the lines below:

      KPL/PCK

      begindata

         BODY399_RADII = ( 6378.137,  6378.137, 6356.752314247833 )

      begintext

   Users who create this file must be sure that the "ID word" KPL/PCK
   occupies the very first 7 characters of the file, and to add a carriage
   return at the end of the file. See the SPICE Toolkit documents "PCK
   Required Reading" and "Kernel Required Reading" for details of the SPICE
   text PCK format.


   Epoch
   -----

   The epoch associated with these data is given by the source as
   "2003.0."  The time variation of the data is slow enough so that
   specification of the time system is unimportant. However, in the
   creation of this file, the epoch is assumed to be

      2003 Jan 1 00:00:00 TDB

   At this epoch, the station positions are as given below.

   The movement of the stations due to tectonic plate motion is taken
   into account in creation of the frame definitions used in this file:
   the center locations and orientations of the reference frames are
   associated with station locations extrapolated to the date

      2026 July 17 00:00:00 TDB

   This extrapolation results in a small rotation of the frames relative
   to their orientations as given by the previous version of this kernel.


   Position data
   -------------

   Station locations in the ITRF93 frame at the specified epoch from [1]
   are:
  
   Table 2. Cartesian Coordinates for DSN Stations in ITRF93 Reference Frame, 
            Epoch 2003.0 {3}

       Antenna  Diameter    x (m)         y (m)         z (m)

       DSS 13   34-m R & D  -2351112.659  -4655530.636  +3660912.728
       DSS 14   70-m        -2353621.420  -4641341.472  +3677052.318
       DSS 15   34-m HEF    -2353538.958  -4641649.429  +3676669.984 {2}
       DSS 23   34-m BWG    -2354702.027  -4646969.709  +3669213.211 {1}
       DSS 24   34-m BWG    -2354906.711  -4646840.095  +3669242.325
       DSS 25   34-m BWG    -2355022.014  -4646953.204  +3669040.567
       DSS 26   34-m BWG    -2354890.797  -4647166.328  +3668871.755
       DSS 33   34-m BWG    -4461103      +2682649      -3674286     {4}
       DSS 34   34-m BWG    -4461147.093  +2682439.239  -3674393.133 {1}
       DSS 35   34-m BWG    -4461273.090  +2682568.925  -3674152.093 {1}
       DSS 36   34-m BWG    -4461168.415  +2682814.657  -3674083.901 {1}
       DSS 43   70-m        -4460894.917  +2682361.507  -3674748.152
       DSS 45   34-m HEF    -4460935.578  +2682765.661  -3674380.982 {2}
       DSS 53   34-m BWG    +4849338.209  -360657.812   +4114746.173 {1}
       DSS 54   34-m BWG    +4849434.488  -360723.8999  +4114618.835
       DSS 55   34-m BWG    +4849525.256  -360606.0932  +4114495.084
       DSS 56   34-m BWG    +4849421.679  -360549.659   +4114646.987 {1}
       DSS 63   70-m        +4849092.518  -360180.3480  +4115109.251
       DSS 65   34-m HEF    +4849339.634  -360427.6637  +4114750.733
 

       Notes from [1]:

       {1} Position absolute accuracy estimated to be +/- 3cm (0.030m)
           (1-sigma) for each coordinate.

       {2} Decommissioned. For historical reference only.

       {3} See Table 7 note under "Accuracy" section below.

       {4} Estimated location, good to a few meters.


   Velocity data
   -------------

   Station velocities in Cartesian coordinates, with respect to the
   ITRF93 frame, are shown below.

       Reference epoch for plate motion: 01-JAN-2003 00:00

       Plate motion model, m/year

                                         X         Y         Z
       Goldstone:

          Stations numbered 1X & 2X   -0.0180    0.0065    -0.0038

       Canberra:

          Stations numbered 3X & 4X   -0.0335   -0.0041     0.0392

       Madrid:

          Stations numbered 5X & 6X   -0.0100    0.0242     0.0156


   Accuracy
   --------
 
   Location uncertainties at the 1 sigma level, for cylindrical coordinates,
   are given by Table 7 of reference [1].

   Table 7 note:

      The numbers in this table represent the uncertainties in 
      location at the time of VLBI measurements. In the years 
      since the measurements, a number of occurrences have 
      conspired to increase the uncertainties to as much as 
      0.1 meter, 1-sigma. This is due to events such as the 2019 
      Ridgecrest earthquake, which affected Goldstone at the 
      level of several centimeters, as well as uncertainty in
      tectonic plate velocities integrating up over the years. 
      The DSS-33 uncertainty is for an estimated location.


   References
   ----------
 
   The data provided here are taken from the DSN document

      [1] "301 Coverage and Geometry." DSN No. 810-005, 301, Rev. P
          Issue Date: May 22, 2026. URS CL#26-1634.

          URL: https://deepspace.jpl.nasa.gov/dsndocs/810-005/301/301P.pdf


   Documentation for the SPICE Toolkit software is available here:

       URL:  https://naif.jpl.nasa.gov


   Kernel Data
   =====================================================================


   EARTH_FIXED alias mapping
   -------------------------

   Constant-offset frame definition for the frame alias EARTH_FIXED:
   EARTH_FIXED is mapped to ITRF93.


\begindata

   TKFRAME_EARTH_FIXED_RELATIVE = 'ITRF93'
   TKFRAME_EARTH_FIXED_SPEC     = 'MATRIX'
   TKFRAME_EARTH_FIXED_MATRIX   = ( 1   0   0
                                    0   1   0
                                    0   0   1 )

\begintext


   Kernel contents below were created by PINPOINT. The output includes
   the full PINPOINT setup file, including its comment area.


   PINPOINT output
   =====================================================================

KPL/FK
 
   FILE: earth_topo_260717.tf
 
   This file was created by PINPOINT.
 
   PINPOINT Version 3.3.0 --- December 13, 2021
   PINPOINT RUN DATE/TIME:    2026-07-17T00:48:02
   PINPOINT DEFINITIONS FILE: earthstns_fx_260717.cmt
   PINPOINT PCK FILE:         earthstns_itrf93_260717.tpc
   PINPOINT SPK FILE:         earthstns_fx_260717.bsp
 
   The input definitions file is appended to this
   file as a comment block.
 
 
   Body-name mapping follows:
 
\begindata
 
   NAIF_BODY_NAME                      += 'DSS-13'
   NAIF_BODY_CODE                      += 399013
 
   NAIF_BODY_NAME                      += 'DSS-14'
   NAIF_BODY_CODE                      += 399014
 
   NAIF_BODY_NAME                      += 'DSS-15'
   NAIF_BODY_CODE                      += 399015
 
   NAIF_BODY_NAME                      += 'DSS-23'
   NAIF_BODY_CODE                      += 399023
 
   NAIF_BODY_NAME                      += 'DSS-24'
   NAIF_BODY_CODE                      += 399024
 
   NAIF_BODY_NAME                      += 'DSS-25'
   NAIF_BODY_CODE                      += 399025
 
   NAIF_BODY_NAME                      += 'DSS-26'
   NAIF_BODY_CODE                      += 399026
 
   NAIF_BODY_NAME                      += 'DSS-33'
   NAIF_BODY_CODE                      += 399033
 
   NAIF_BODY_NAME                      += 'DSS-34'
   NAIF_BODY_CODE                      += 399034
 
   NAIF_BODY_NAME                      += 'DSS-35'
   NAIF_BODY_CODE                      += 399035
 
   NAIF_BODY_NAME                      += 'DSS-36'
   NAIF_BODY_CODE                      += 399036
 
   NAIF_BODY_NAME                      += 'DSS-43'
   NAIF_BODY_CODE                      += 399043
 
   NAIF_BODY_NAME                      += 'DSS-45'
   NAIF_BODY_CODE                      += 399045
 
   NAIF_BODY_NAME                      += 'DSS-53'
   NAIF_BODY_CODE                      += 399053
 
   NAIF_BODY_NAME                      += 'DSS-54'
   NAIF_BODY_CODE                      += 399054
 
   NAIF_BODY_NAME                      += 'DSS-55'
   NAIF_BODY_CODE                      += 399055
 
   NAIF_BODY_NAME                      += 'DSS-56'
   NAIF_BODY_CODE                      += 399056
 
   NAIF_BODY_NAME                      += 'DSS-63'
   NAIF_BODY_CODE                      += 399063
 
   NAIF_BODY_NAME                      += 'DSS-65'
   NAIF_BODY_CODE                      += 399065
 
\begintext
 
 
   Reference frame specifications follow:
 
 
   Topocentric frame DSS-13_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-13_TOPO is centered at the
      site DSS-13, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                 -0.2351113082721E+04
         Y (km):                 -0.4655530482990E+04
         Z (km):                  0.3660912638548E+04
 
      and planetodetic coordinates
 
         Longitude (deg):      -116.7944639106750
         Latitude  (deg):        35.2471633142906
         Altitude   (km):         0.1070437773660E+01
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-13_TOPO                   =  1399013
   FRAME_1399013_NAME                  =  'DSS-13_TOPO'
   FRAME_1399013_CLASS                 =  4
   FRAME_1399013_CLASS_ID              =  1399013
   FRAME_1399013_CENTER                =  399013
 
   OBJECT_399013_FRAME                 =  'DSS-13_TOPO'
 
   TKFRAME_1399013_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399013_SPEC                =  'ANGLES'
   TKFRAME_1399013_UNITS               =  'DEGREES'
   TKFRAME_1399013_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399013_ANGLES              =  ( -243.2055360893250,
                                             -54.7528366857094,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-14_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-14_TOPO is centered at the
      site DSS-14, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                 -0.2353621843721E+04
         Y (km):                 -0.4641341318990E+04
         Z (km):                  0.3677052228548E+04
 
      and planetodetic coordinates
 
         Longitude (deg):      -116.8895431330483
         Latitude  (deg):        35.4258999225138
         Altitude   (km):         0.1001384087429E+01
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-14_TOPO                   =  1399014
   FRAME_1399014_NAME                  =  'DSS-14_TOPO'
   FRAME_1399014_CLASS                 =  4
   FRAME_1399014_CLASS_ID              =  1399014
   FRAME_1399014_CENTER                =  399014
 
   OBJECT_399014_FRAME                 =  'DSS-14_TOPO'
 
   TKFRAME_1399014_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399014_SPEC                =  'ANGLES'
   TKFRAME_1399014_UNITS               =  'DEGREES'
   TKFRAME_1399014_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399014_ANGLES              =  ( -243.1104568669517,
                                             -54.5741000774862,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-15_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-15_TOPO is centered at the
      site DSS-15, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                 -0.2353539381721E+04
         Y (km):                 -0.4641649275990E+04
         Z (km):                  0.3676669894548E+04
 
      and planetodetic coordinates
 
         Longitude (deg):      -116.8872000291808
         Latitude  (deg):        35.4218523322741
         Altitude   (km):         0.9732047687674E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-15_TOPO                   =  1399015
   FRAME_1399015_NAME                  =  'DSS-15_TOPO'
   FRAME_1399015_CLASS                 =  4
   FRAME_1399015_CLASS_ID              =  1399015
   FRAME_1399015_CENTER                =  399015
 
   OBJECT_399015_FRAME                 =  'DSS-15_TOPO'
 
   TKFRAME_1399015_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399015_SPEC                =  'ANGLES'
   TKFRAME_1399015_UNITS               =  'DEGREES'
   TKFRAME_1399015_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399015_ANGLES              =  ( -243.1127999708192,
                                             -54.5781476677259,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-23_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-23_TOPO is centered at the
      site DSS-23, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                 -0.2354702450721E+04
         Y (km):                 -0.4646969555990E+04
         Z (km):                  0.3669213121548E+04
 
      and planetodetic coordinates
 
         Longitude (deg):      -116.8721468595840
         Latitude  (deg):        35.3395574335843
         Altitude   (km):         0.9535039445097E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-23_TOPO                   =  1399023
   FRAME_1399023_NAME                  =  'DSS-23_TOPO'
   FRAME_1399023_CLASS                 =  4
   FRAME_1399023_CLASS_ID              =  1399023
   FRAME_1399023_CENTER                =  399023
 
   OBJECT_399023_FRAME                 =  'DSS-23_TOPO'
 
   TKFRAME_1399023_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399023_SPEC                =  'ANGLES'
   TKFRAME_1399023_UNITS               =  'DEGREES'
   TKFRAME_1399023_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399023_ANGLES              =  ( -243.1278531404160,
                                             -54.6604425664157,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-24_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-24_TOPO is centered at the
      site DSS-24, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                 -0.2354907134721E+04
         Y (km):                 -0.4646839941990E+04
         Z (km):                  0.3669242235548E+04
 
      and planetodetic coordinates
 
         Longitude (deg):      -116.8747993056580
         Latitude  (deg):        35.3398918502587
         Altitude   (km):         0.9515047556156E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-24_TOPO                   =  1399024
   FRAME_1399024_NAME                  =  'DSS-24_TOPO'
   FRAME_1399024_CLASS                 =  4
   FRAME_1399024_CLASS_ID              =  1399024
   FRAME_1399024_CENTER                =  399024
 
   OBJECT_399024_FRAME                 =  'DSS-24_TOPO'
 
   TKFRAME_1399024_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399024_SPEC                =  'ANGLES'
   TKFRAME_1399024_UNITS               =  'DEGREES'
   TKFRAME_1399024_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399024_ANGLES              =  ( -243.1252006943420,
                                             -54.6601081497413,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-25_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-25_TOPO is centered at the
      site DSS-25, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                 -0.2355022437721E+04
         Y (km):                 -0.4646953050990E+04
         Z (km):                  0.3669040477548E+04
 
      and planetodetic coordinates
 
         Longitude (deg):      -116.8753681220643
         Latitude  (deg):        35.3376110213864
         Altitude   (km):         0.9596274206088E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-25_TOPO                   =  1399025
   FRAME_1399025_NAME                  =  'DSS-25_TOPO'
   FRAME_1399025_CLASS                 =  4
   FRAME_1399025_CLASS_ID              =  1399025
   FRAME_1399025_CENTER                =  399025
 
   OBJECT_399025_FRAME                 =  'DSS-25_TOPO'
 
   TKFRAME_1399025_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399025_SPEC                =  'ANGLES'
   TKFRAME_1399025_UNITS               =  'DEGREES'
   TKFRAME_1399025_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399025_ANGLES              =  ( -243.1246318779357,
                                             -54.6623889786136,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-26_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-26_TOPO is centered at the
      site DSS-26, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                 -0.2354891220721E+04
         Y (km):                 -0.4647166174990E+04
         Z (km):                  0.3668871665548E+04
 
      and planetodetic coordinates
 
         Longitude (deg):      -116.8730213369531
         Latitude  (deg):        35.3356882367043
         Altitude   (km):         0.9686862799500E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-26_TOPO                   =  1399026
   FRAME_1399026_NAME                  =  'DSS-26_TOPO'
   FRAME_1399026_CLASS                 =  4
   FRAME_1399026_CLASS_ID              =  1399026
   FRAME_1399026_CENTER                =  399026
 
   OBJECT_399026_FRAME                 =  'DSS-26_TOPO'
 
   TKFRAME_1399026_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399026_SPEC                =  'ANGLES'
   TKFRAME_1399026_UNITS               =  'DEGREES'
   TKFRAME_1399026_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399026_ANGLES              =  ( -243.1269786630468,
                                             -54.6643117632957,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-33_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-33_TOPO is centered at the
      site DSS-33, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                  0.4461102211409E+04
         Y (km):                  0.2682648903486E+04
         Z (km):                 -0.3674285077230E+04
 
      and planetodetic coordinates
 
         Longitude (deg):        31.0202678466005
         Latitude  (deg):       -35.3973217797648
         Altitude   (km):         0.6861490242750E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-33_TOPO                   =  1399033
   FRAME_1399033_NAME                  =  'DSS-33_TOPO'
   FRAME_1399033_CLASS                 =  4
   FRAME_1399033_CLASS_ID              =  1399033
   FRAME_1399033_CENTER                =  399033
 
   OBJECT_399033_FRAME                 =  'DSS-33_TOPO'
 
   TKFRAME_1399033_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399033_SPEC                =  'ANGLES'
   TKFRAME_1399033_UNITS               =  'DEGREES'
   TKFRAME_1399033_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399033_ANGLES              =  (  -31.0202678466005,
                                            -125.3973217797648,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-34_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-34_TOPO is centered at the
      site DSS-34, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                 -0.4461147881591E+04
         Y (km):                  0.2682439142486E+04
         Z (km):                 -0.3674392210230E+04
 
      and planetodetic coordinates
 
         Longitude (deg):       148.9819698029999
         Latitude  (deg):       -35.3984687898841
         Altitude   (km):         0.6919966378344E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-34_TOPO                   =  1399034
   FRAME_1399034_NAME                  =  'DSS-34_TOPO'
   FRAME_1399034_CLASS                 =  4
   FRAME_1399034_CLASS_ID              =  1399034
   FRAME_1399034_CENTER                =  399034
 
   OBJECT_399034_FRAME                 =  'DSS-34_TOPO'
 
   TKFRAME_1399034_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399034_SPEC                =  'ANGLES'
   TKFRAME_1399034_UNITS               =  'DEGREES'
   TKFRAME_1399034_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399034_ANGLES              =  ( -148.9819698029999,
                                            -125.3984687898841,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-35_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-35_TOPO is centered at the
      site DSS-35, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                 -0.4461273878591E+04
         Y (km):                  0.2682568828486E+04
         Z (km):                 -0.3674151170230E+04
 
      and planetodetic coordinates
 
         Longitude (deg):       148.9814611499880
         Latitude  (deg):       -35.3957854660205
         Altitude   (km):         0.6948728946958E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-35_TOPO                   =  1399035
   FRAME_1399035_NAME                  =  'DSS-35_TOPO'
   FRAME_1399035_CLASS                 =  4
   FRAME_1399035_CLASS_ID              =  1399035
   FRAME_1399035_CENTER                =  399035
 
   OBJECT_399035_FRAME                 =  'DSS-35_TOPO'
 
   TKFRAME_1399035_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399035_SPEC                =  'ANGLES'
   TKFRAME_1399035_UNITS               =  'DEGREES'
   TKFRAME_1399035_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399035_ANGLES              =  ( -148.9814611499880,
                                            -125.3957854660205,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-36_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-36_TOPO is centered at the
      site DSS-36, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                 -0.4461169203591E+04
         Y (km):                  0.2682814560486E+04
         Z (km):                 -0.3674082978230E+04
 
      and planetodetic coordinates
 
         Longitude (deg):       148.9785496161747
         Latitude  (deg):       -35.3950917143419
         Altitude   (km):         0.6854790782515E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-36_TOPO                   =  1399036
   FRAME_1399036_NAME                  =  'DSS-36_TOPO'
   FRAME_1399036_CLASS                 =  4
   FRAME_1399036_CLASS_ID              =  1399036
   FRAME_1399036_CENTER                =  399036
 
   OBJECT_399036_FRAME                 =  'DSS-36_TOPO'
 
   TKFRAME_1399036_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399036_SPEC                =  'ANGLES'
   TKFRAME_1399036_UNITS               =  'DEGREES'
   TKFRAME_1399036_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399036_ANGLES              =  ( -148.9785496161747,
                                            -125.3950917143419,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-43_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-43_TOPO is centered at the
      site DSS-43, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                 -0.4460895705591E+04
         Y (km):                  0.2682361410486E+04
         Z (km):                 -0.3674747229230E+04
 
      and planetodetic coordinates
 
         Longitude (deg):       148.9812726938012
         Latitude  (deg):       -35.4024141881635
         Altitude   (km):         0.6888431941637E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-43_TOPO                   =  1399043
   FRAME_1399043_NAME                  =  'DSS-43_TOPO'
   FRAME_1399043_CLASS                 =  4
   FRAME_1399043_CLASS_ID              =  1399043
   FRAME_1399043_CENTER                =  399043
 
   OBJECT_399043_FRAME                 =  'DSS-43_TOPO'
 
   TKFRAME_1399043_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399043_SPEC                =  'ANGLES'
   TKFRAME_1399043_UNITS               =  'DEGREES'
   TKFRAME_1399043_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399043_ANGLES              =  ( -148.9812726938012,
                                            -125.4024141881635,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-45_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-45_TOPO is centered at the
      site DSS-45, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                 -0.4460936366591E+04
         Y (km):                  0.2682765564486E+04
         Z (km):                 -0.3674380059230E+04
 
      and planetodetic coordinates
 
         Longitude (deg):       148.9776910173395
         Latitude  (deg):       -35.3984476368870
         Altitude   (km):         0.6743227714049E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-45_TOPO                   =  1399045
   FRAME_1399045_NAME                  =  'DSS-45_TOPO'
   FRAME_1399045_CLASS                 =  4
   FRAME_1399045_CLASS_ID              =  1399045
   FRAME_1399045_CENTER                =  399045
 
   OBJECT_399045_FRAME                 =  'DSS-45_TOPO'
 
   TKFRAME_1399045_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399045_SPEC                =  'ANGLES'
   TKFRAME_1399045_UNITS               =  'DEGREES'
   TKFRAME_1399045_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399045_ANGLES              =  ( -148.9776910173395,
                                            -125.3984476368870,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-53_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-53_TOPO is centered at the
      site DSS-53, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                  0.4849337973600E+04
         Y (km):                 -0.3606572423310E+03
         Z (km):                  0.4114746540225E+04
 
      and planetodetic coordinates
 
         Longitude (deg):        -4.2533979467262
         Latitude  (deg):        40.4270878990369
         Altitude   (km):         0.8428328685475E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-53_TOPO                   =  1399053
   FRAME_1399053_NAME                  =  'DSS-53_TOPO'
   FRAME_1399053_CLASS                 =  4
   FRAME_1399053_CLASS_ID              =  1399053
   FRAME_1399053_CENTER                =  399053
 
   OBJECT_399053_FRAME                 =  'DSS-53_TOPO'
 
   TKFRAME_1399053_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399053_SPEC                =  'ANGLES'
   TKFRAME_1399053_UNITS               =  'DEGREES'
   TKFRAME_1399053_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399053_ANGLES              =  ( -355.7466020532738,
                                             -49.5729121009631,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-54_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-54_TOPO is centered at the
      site DSS-54, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                  0.4849434252600E+04
         Y (km):                 -0.3607233302310E+03
         Z (km):                  0.4114619202225E+04
 
      and planetodetic coordinates
 
         Longitude (deg):        -4.2540903399609
         Latitude  (deg):        40.4256258126786
         Altitude   (km):         0.8370791021059E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-54_TOPO                   =  1399054
   FRAME_1399054_NAME                  =  'DSS-54_TOPO'
   FRAME_1399054_CLASS                 =  4
   FRAME_1399054_CLASS_ID              =  1399054
   FRAME_1399054_CENTER                =  399054
 
   OBJECT_399054_FRAME                 =  'DSS-54_TOPO'
 
   TKFRAME_1399054_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399054_SPEC                =  'ANGLES'
   TKFRAME_1399054_UNITS               =  'DEGREES'
   TKFRAME_1399054_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399054_ANGLES              =  ( -355.7459096600391,
                                             -49.5743741873214,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-55_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-55_TOPO is centered at the
      site DSS-55, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                  0.4849525020600E+04
         Y (km):                 -0.3606055235310E+03
         Z (km):                  0.4114495451225E+04
 
      and planetodetic coordinates
 
         Longitude (deg):        -4.2526268118590
         Latitude  (deg):        40.4243000374531
         Altitude   (km):         0.8190885611009E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-55_TOPO                   =  1399055
   FRAME_1399055_NAME                  =  'DSS-55_TOPO'
   FRAME_1399055_CLASS                 =  4
   FRAME_1399055_CLASS_ID              =  1399055
   FRAME_1399055_CENTER                =  399055
 
   OBJECT_399055_FRAME                 =  'DSS-55_TOPO'
 
   TKFRAME_1399055_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399055_SPEC                =  'ANGLES'
   TKFRAME_1399055_UNITS               =  'DEGREES'
   TKFRAME_1399055_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399055_ANGLES              =  ( -355.7473731881410,
                                             -49.5756999625469,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-56_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-56_TOPO is centered at the
      site DSS-56, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                  0.4849421443600E+04
         Y (km):                 -0.3605490893310E+03
         Z (km):                  0.4114647354225E+04
 
      and planetodetic coordinates
 
         Longitude (deg):        -4.2520542064524
         Latitude  (deg):        40.4259688186567
         Altitude   (km):         0.8357738086113E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-56_TOPO                   =  1399056
   FRAME_1399056_NAME                  =  'DSS-56_TOPO'
   FRAME_1399056_CLASS                 =  4
   FRAME_1399056_CLASS_ID              =  1399056
   FRAME_1399056_CENTER                =  399056
 
   OBJECT_399056_FRAME                 =  'DSS-56_TOPO'
 
   TKFRAME_1399056_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399056_SPEC                =  'ANGLES'
   TKFRAME_1399056_UNITS               =  'DEGREES'
   TKFRAME_1399056_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399056_ANGLES              =  ( -355.7479457935476,
                                             -49.5740311813433,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-63_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-63_TOPO is centered at the
      site DSS-63, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                  0.4849092282600E+04
         Y (km):                 -0.3601797783310E+03
         Z (km):                  0.4115109618225E+04
 
      and planetodetic coordinates
 
         Longitude (deg):        -4.2480020535013
         Latitude  (deg):        40.4312138842194
         Altitude   (km):         0.8648448375319E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-63_TOPO                   =  1399063
   FRAME_1399063_NAME                  =  'DSS-63_TOPO'
   FRAME_1399063_CLASS                 =  4
   FRAME_1399063_CLASS_ID              =  1399063
   FRAME_1399063_CENTER                =  399063
 
   OBJECT_399063_FRAME                 =  'DSS-63_TOPO'
 
   TKFRAME_1399063_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399063_SPEC                =  'ANGLES'
   TKFRAME_1399063_UNITS               =  'DEGREES'
   TKFRAME_1399063_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399063_ANGLES              =  ( -355.7519979464987,
                                             -49.5687861157806,
                                             180.0000000000000 )
 
 
\begintext
 
   Topocentric frame DSS-65_TOPO
 
      The Z axis of this frame points toward the zenith.
      The X axis of this frame points North.
 
      Topocentric frame DSS-65_TOPO is centered at the
      site DSS-65, which at the epoch
 
          2026 JUL 17 00:00:00.000 TDB
 
      has Cartesian coordinates
 
         X (km):                  0.4849339398600E+04
         Y (km):                 -0.3604270940310E+03
         Z (km):                  0.4114751100225E+04
 
      and planetodetic coordinates
 
         Longitude (deg):        -4.2506924082707
         Latitude  (deg):        40.4272104971196
         Altitude   (km):         0.8338819580633E+00
 
      These planetodetic coordinates are expressed relative to
      a reference spheroid having the dimensions
 
         Equatorial radius (km):  6.3781370000000E+03
         Polar radius      (km):  6.3567523142478E+03
 
      All of the above coordinates are relative to the frame EARTH_FIXED.
 
 
\begindata
 
   FRAME_DSS-65_TOPO                   =  1399065
   FRAME_1399065_NAME                  =  'DSS-65_TOPO'
   FRAME_1399065_CLASS                 =  4
   FRAME_1399065_CLASS_ID              =  1399065
   FRAME_1399065_CENTER                =  399065
 
   OBJECT_399065_FRAME                 =  'DSS-65_TOPO'
 
   TKFRAME_1399065_RELATIVE            =  'EARTH_FIXED'
   TKFRAME_1399065_SPEC                =  'ANGLES'
   TKFRAME_1399065_UNITS               =  'DEGREES'
   TKFRAME_1399065_AXES                =  ( 3, 2, 3 )
   TKFRAME_1399065_ANGLES              =  ( -355.7493075917293,
                                             -49.5727895028804,
                                             180.0000000000000 )
 
\begintext
 
 
Definitions file earthstns_fx_260717.cmt
--------------------------------------------------------------------------------
 
 
   SPK for DSN Station Locations
   =====================================================================
 
   Original file name:                   earthstns_fx_260717.bsp
   Creation date:                        2026 July 17 00:42
   Created by:                           Nat Bachman  (NAIF/JPL)
 
 
   Introduction
   =====================================================================
 
   This file provides geocentric states---locations and velocities---for the
   set of DSN stations cited in the list below under "Position Data." Station
   position vectors point from the earth's barycenter to the stations. Station
   velocities are estimates of the derivatives with respect to time of these
   vectors; in this file, velocities are constant. Station velocities have
   magnitudes on the order of a few cm/year.
 
   The states in this file are given relative to the terrestrial reference
   frame ITRF93. In the interest of flexibility, in this file the reference
   frame is labeled with the alias 'EARTH_FIXED'. Any application using this
   file must map the alias 'EARTH_FIXED' to either 'ITRF93' or 'IAU_EARTH'.
   See the discussion below under "Reference frame alias" for details.
 
   This SPK file has a companion file
 
      earthstns_itrf93_260717.bsp
 
   which differs from this one only in that it uses the reference frame name
   'ITRF93'. For high-accuracy work, the companion file is recommended (on the
   basis of ease of use).
 
 
   Revision description
   --------------------
 
   This kernel contains data from a single, current source: [1].
 
   This kernel supersedes the kernels
 
      earthstns_fx_201023.bsp
      dss_23_placeholder_itrf93_201017.bsp
 
   The set of stations covered by this file has changed from that of the file
 
      earthstns_fx_201023.bsp
 
   as follows:
 
      Deleted stations (not present in current file):
 
         None.
 
      Added stations:
 
         DSS-23
         DSS-33
 
      Changed data:
 
         DSS-53
 
 
   Planned updates
   ---------------
 
   Updates will be be made to keep this file in sync with updates to the
   source document [1].
 
 
   Using this kernel
   =====================================================================
 
   Kernel loading
   --------------
 
   In order for a SPICE-based program to make use of this kernel, the
   kernel must be loaded via the SPICE routine FURNSH. If you are
   running application software created by a third party, see the
   documentation for that software for instructions on kernel
   management.
 
   See also "Associated frame kernels" and "Associated PCK files"
   below.
 
   Users requiring data from superseded SPK versions can load those files
   in addition to this one. In the case of conflicting data, data from SPKs
   loaded later take precedence over SPKs loaded earlier.
 
 
   Reference frame alias
   ---------------------
 
   This kernel uses the alias 'EARTH_FIXED' to designate the reference frame
   relative to which the data in this kernel are specified. In order for this
   kernel to be usable, the alias must be mapped to the name of a supported
   terrestrial frame. For high-accuracy work, the frame name 'ITRF93' should
   be used. In some situations, for example when low accuracy, long term
   predictions are desired, it may be convenient to map 'EARTH_FIXED'
   to 'IAU_EARTH'.
 
   To map the alias, an application must load a text kernel containing
   assignments as shown below.
 
      begintext
 
      Map 'EARTH_FIXED' to ITRF93.  (To map to IAU_EARTH, substitute
      'IAU_EARTH' for 'ITRF93' below.)
 
      begindata
 
         TKFRAME_EARTH_FIXED_RELATIVE = 'ITRF93'
         TKFRAME_EARTH_FIXED_SPEC     = 'MATRIX'
         TKFRAME_EARTH_FIXED_MATRIX   = ( 1   0   0
                                          0   1   0
                                          0   0   1 )
 
      begintext
 
 
   See the Frames Required Reading for details.
 
 
   Associated PCK files
   --------------------
 
   For high-accuracy work, this kernel should be used together with a
   high-precision, binary earth PCK file.
 
      NAIF produces these kernels on a regular basis; they can be
      obtained via anonymous ftp from the NAIF server
 
         naif.jpl.nasa.gov
 
      or downloaded from the URL
 
         https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/
 
      The PCK is located in the path
 
         pub/naif/generic_kernels/pck
 
      The file name is of the form
 
         earth_000101_yymmdd_yymmdd.bpc
 
      The first two dates are the file's start and stop times; the third
      is the epoch of the last datum in the EOP file:  data from
      this epoch forward are predicted.
 
      The file's coverage starts at a fixed date (currently chosen to
      be 2000 Jan. 1) and extends to the end of the predict region,
      which has a duration of roughly 3 months.
 
      The same location contains a file with identical contents and a fixed
      name:
 
         earth_latest_high_prec.bpc
 
      This file may be convenient for automated downloads.
 
      NAIF also provides a low-accuracy, long-term predict binary Earth PCK.
      See the file
 
          aareadme.txt
 
      in the location cited above for details.
 
 
   Associated frame kernels
   ------------------------
 
   The frame kernel having (original) file name
 
      earth_topo_260717.tf
 
   defines topocentric reference frames associated with each of
   the stations covered by this file. That kernel supports
   computations such as finding the azimuth and elevation of a target
   as seen from a specified station.
 
 
   Data sources
   =====================================================================
 
   All data presented here are from reference [1].
 
 
   Reference Spheroid
   ------------------
 
   The reference bi-axial spheroid is defined by an equatorial and a
   polar radius. Calling these Re and Rp respectively, the flattening
   factor f is defined as
 
      f = ( Re - Rp ) / Re
 
   For the reference spheroid used by this file, the equatorial radius
   Re and inverse flattening factor 1/f are
 
      Re  = 6378137 m
      1/f = 298.2572236
 
   The reference spheroid is not used for the creation of this SPK file
   but is used to create the associated frame kernel named above.
 
 
   Epoch
   -----
 
   The epoch associated with these data is given by the source as
   "2003.0."  The time variation of the data is slow enough so that
   specification of the time system is unimportant. However, in the
   creation of this file, the epoch is assumed to be
 
      2003 Jan 1 00:00:00 TDB
 
   At this epoch, the station positions are as given below.
 
 
   Position data
   -------------
 
   From [1]:
 
   Table 2. Cartesian Coordinates for DSN Stations in ITRF93 Reference Frame,
            Epoch 2003.0 {3}
 
       Antenna  Diameter    x (m)         y (m)         z (m)
 
       DSS 13   34-m R & D  -2351112.659  -4655530.636  +3660912.728
       DSS 14   70-m        -2353621.420  -4641341.472  +3677052.318
       DSS 15   34-m HEF    -2353538.958  -4641649.429  +3676669.984 {2}
       DSS 23   34-m BWG    -2354702.027  -4646969.709  +3669213.211 {1}
       DSS 24   34-m BWG    -2354906.711  -4646840.095  +3669242.325
       DSS 25   34-m BWG    -2355022.014  -4646953.204  +3669040.567
       DSS 26   34-m BWG    -2354890.797  -4647166.328  +3668871.755
       DSS 33   34-m BWG    -4461103      +2682649      -3674286     {4}
       DSS 34   34-m BWG    -4461147.093  +2682439.239  -3674393.133 {1}
       DSS 35   34-m BWG    -4461273.090  +2682568.925  -3674152.093 {1}
       DSS 36   34-m BWG    -4461168.415  +2682814.657  -3674083.901 {1}
       DSS 43   70-m        -4460894.917  +2682361.507  -3674748.152
       DSS 45   34-m HEF    -4460935.578  +2682765.661  -3674380.982 {2}
       DSS 53   34-m BWG    +4849338.209  -360657.812   +4114746.173 {1}
       DSS 54   34-m BWG    +4849434.488  -360723.8999  +4114618.835
       DSS 55   34-m BWG    +4849525.256  -360606.0932  +4114495.084
       DSS 56   34-m BWG    +4849421.679  -360549.659   +4114646.987 {1}
       DSS 63   70-m        +4849092.518  -360180.3480  +4115109.251
       DSS 65   34-m HEF    +4849339.634  -360427.6637  +4114750.733
 
 
       Notes from [1]:
 
       {1} Position absolute accuracy estimated to be +/- 3cm (0.030m)
           (1-sigma) for each coordinate.
 
       {2} Decommissioned. For historical reference only.
 
       {3} See Table 7 note under "Accuracy" section below.
 
       {4} Estimated location, good to a few meters.
 
 
   Velocity data
   -------------
 
   Station velocities in Cartesian coordinates, with respect to the
   ITRF93 frame, are shown below.
 
       Reference epoch for plate motion: 01-JAN-2003 00:00
 
       Plate motion model, m/year
 
                                         X         Y         Z
       Goldstone:
 
          Stations numbered 1X & 2X   -0.0180    0.0065    -0.0038
 
       Canberra:
 
          Stations numbered 3X & 4X   -0.0335   -0.0041     0.0392
 
       Madrid:
 
          Stations numbered 5X & 6X   -0.0100    0.0242     0.0156
 
 
   Accuracy
   --------
 
   Location uncertainties at the 1 sigma level, for cylindrical coordinates,
   are given by Table 7 of reference [1].
 
   Table 7 note:
 
      The numbers in this table represent the uncertainties in
      location at the time of VLBI measurements. In the years
      since the measurements, a number of occurrences have
      conspired to increase the uncertainties to as much as
      0.1 meter, 1-sigma. This is due to events such as the 2019
      Ridgecrest earthquake, which affected Goldstone at the
      level of several centimeters, as well as uncertainty in
      tectonic plate velocities integrating up over the years.
      The DSS-33 uncertainty is for an estimated location.
 
 
   References
   ----------
 
   The data provided here are taken from the DSN document
 
      [1] "301 Coverage and Geometry." DSN No. 810-005, 301, Rev. P
          Issue Date: May 22, 2026. URS CL#26-1634.
 
          URL: https://deepspace.jpl.nasa.gov/dsndocs/810-005/301/301P.pdf
 
 
   Documentation for the SPICE Toolkit software is available here:
 
       URL:  https://naif.jpl.nasa.gov
 
 
   Kernel Data
   =====================================================================
 
begintext
 
   Station locations and velocities, along with topocentric reference frame
   specification parameters:
 
begindata
 
 
   SITES            +=      'DSS-13'
   DSS-13_FRAME      =       'EARTH_FIXED'
   DSS-13_CENTER     =       399
   DSS-13_IDCODE     =       399013
   DSS-13_EPOCH      =       @2003-JAN-01/00:00
   DSS-13_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-13_XYZ        =    ( -2351.112659    -4655.530636    +3660.912728 )
   DSS-13_DXYZ       =    (    -0.0180          0.0065         -0.0038   )
   DSS-13_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-13_UP         =       'Z'
   DSS-13_NORTH      =       'X'
 
 
   SITES            +=      'DSS-14'
   DSS-14_FRAME      =       'EARTH_FIXED'
   DSS-14_CENTER     =       399
   DSS-14_IDCODE     =       399014
   DSS-14_EPOCH      =       @2003-JAN-01/00:00
   DSS-14_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-14_XYZ        =    ( -2353.621420    -4641.341472    +3677.052318 )
   DSS-14_DXYZ       =    (    -0.0180          0.0065         -0.0038   )
   DSS-14_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-14_UP         =       'Z'
   DSS-14_NORTH      =       'X'
 
 
   SITES            +=      'DSS-15'
   DSS-15_FRAME      =       'EARTH_FIXED'
   DSS-15_CENTER     =       399
   DSS-15_IDCODE     =       399015
   DSS-15_EPOCH      =       @2003-JAN-01/00:00
   DSS-15_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-15_XYZ        =    ( -2353.538958    -4641.649429    +3676.669984 )
   DSS-15_DXYZ       =    (    -0.0180          0.0065         -0.0038   )
   DSS-15_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-15_UP         =       'Z'
   DSS-15_NORTH      =       'X'
 
 
   SITES            +=      'DSS-23'
   DSS-23_FRAME      =       'EARTH_FIXED'
   DSS-23_CENTER     =       399
   DSS-23_IDCODE     =       399023
   DSS-23_EPOCH      =       @2003-JAN-01/00:00
   DSS-23_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-23_XYZ        =    ( -2354.702027    -4646.969709    +3669.213211)
   DSS-23_DXYZ       =    (    -0.0180          0.0065         -0.0038   )
   DSS-23_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-23_UP         =       'Z'
   DSS-23_NORTH      =       'X'
 
 
   SITES            +=      'DSS-24'
   DSS-24_FRAME      =       'EARTH_FIXED'
   DSS-24_CENTER     =       399
   DSS-24_IDCODE     =       399024
   DSS-24_EPOCH      =       @2003-JAN-01/00:00
   DSS-24_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-24_XYZ        =    ( -2354.906711    -4646.840095    +3669.242325 )
   DSS-24_DXYZ       =    (    -0.0180          0.0065         -0.0038   )
   DSS-24_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-24_UP         =       'Z'
   DSS-24_NORTH      =       'X'
 
 
   SITES            +=      'DSS-25'
   DSS-25_FRAME      =       'EARTH_FIXED'
   DSS-25_CENTER     =       399
   DSS-25_IDCODE     =       399025
   DSS-25_EPOCH      =       @2003-JAN-01/00:00
   DSS-25_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-25_XYZ        =    ( -2355.022014    -4646.953204    +3669.040567 )
   DSS-25_DXYZ       =    (    -0.0180          0.0065         -0.0038   )
   DSS-25_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-25_UP         =       'Z'
   DSS-25_NORTH      =       'X'
 
 
   SITES            +=      'DSS-26'
   DSS-26_FRAME      =       'EARTH_FIXED'
   DSS-26_CENTER     =       399
   DSS-26_IDCODE     =       399026
   DSS-26_EPOCH      =       @2003-JAN-01/00:00
   DSS-26_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-26_XYZ        =    ( -2354.890797    -4647.166328    +3668.871755 )
   DSS-26_DXYZ       =    (    -0.0180          0.0065         -0.0038   )
   DSS-26_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-26_UP         =       'Z'
   DSS-26_NORTH      =       'X'
 
 
   SITES            +=      'DSS-33'
   DSS-33_FRAME      =       'EARTH_FIXED'
   DSS-33_CENTER     =       399
   DSS-33_IDCODE     =       399033
   DSS-33_EPOCH      =       @2003-JAN-01/00:00
   DSS-33_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-33_XYZ        =    (  4461.103       +2682.649       -3674.286)
   DSS-33_DXYZ       =    (    -0.0335         -0.0041          0.0392   )
   DSS-33_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-33_UP         =       'Z'
   DSS-33_NORTH      =       'X'
 
 
   SITES            +=      'DSS-34'
   DSS-34_FRAME      =       'EARTH_FIXED'
   DSS-34_CENTER     =       399
   DSS-34_IDCODE     =       399034
   DSS-34_EPOCH      =       @2003-JAN-01/00:00
   DSS-34_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-34_XYZ        =    ( -4461.147093    +2682.439239    -3674.393133 )
   DSS-34_DXYZ       =    (    -0.0335         -0.0041          0.0392   )
   DSS-34_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-34_UP         =       'Z'
   DSS-34_NORTH      =       'X'
 
 
   SITES            +=      'DSS-35'
   DSS-35_FRAME      =       'EARTH_FIXED'
   DSS-35_CENTER     =       399
   DSS-35_IDCODE     =       399035
   DSS-35_EPOCH      =       @2003-JAN-01/00:00
   DSS-35_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-35_XYZ        =    ( -4461.273090    +2682.568925    -3674.152093 )
   DSS-35_DXYZ       =    (    -0.0335         -0.0041          0.0392   )
   DSS-35_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-35_UP         =       'Z'
   DSS-35_NORTH      =       'X'
 
 
   SITES            +=      'DSS-36'
   DSS-36_FRAME      =       'EARTH_FIXED'
   DSS-36_CENTER     =       399
   DSS-36_IDCODE     =       399036
   DSS-36_EPOCH      =       @2003-JAN-01/00:00
   DSS-36_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-36_XYZ        =    ( -4461.168415    +2682.814657    -3674.083901 )
   DSS-36_DXYZ       =    (    -0.0335         -0.0041          0.0392   )
   DSS-36_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-36_UP         =       'Z'
   DSS-36_NORTH      =       'X'
 
 
   SITES            +=      'DSS-43'
   DSS-43_FRAME      =       'EARTH_FIXED'
   DSS-43_CENTER     =       399
   DSS-43_IDCODE     =       399043
   DSS-43_EPOCH      =       @2003-JAN-01/00:00
   DSS-43_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-43_XYZ        =    (   -4460.894917    +2682.361507    -3674.748152 )
   DSS-43_DXYZ       =    (      -0.0335         -0.0041          0.0392   )
   DSS-43_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-43_UP         =       'Z'
   DSS-43_NORTH      =       'X'
 
 
   SITES            +=      'DSS-45'
   DSS-45_FRAME      =       'EARTH_FIXED'
   DSS-45_CENTER     =       399
   DSS-45_IDCODE     =       399045
   DSS-45_EPOCH      =       @2003-JAN-01/00:00
   DSS-45_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-45_XYZ        =    (  -4460.935578    +2682.765661    -3674.380982 )
   DSS-45_DXYZ       =    (     -0.0335         -0.0041          0.0392   )
   DSS-45_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-45_UP         =       'Z'
   DSS-45_NORTH      =       'X'
 
 
   SITES            +=      'DSS-53'
   DSS-53_FRAME      =       'EARTH_FIXED'
   DSS-53_CENTER     =       399
   DSS-53_IDCODE     =       399053
   DSS-53_EPOCH      =       @2003-JAN-01/00:00
   DSS-53_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-53_XYZ        =    (  +4849.338209   -360.657812     +4114.746173 )
   DSS-53_DXYZ       =    (       -0.0100          0.0242          0.0156 )
   DSS-53_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-53_UP         =       'Z'
   DSS-53_NORTH      =       'X'
 
 
   SITES            +=      'DSS-54'
   DSS-54_FRAME      =       'EARTH_FIXED'
   DSS-54_CENTER     =       399
   DSS-54_IDCODE     =       399054
   DSS-54_EPOCH      =       @2003-JAN-01/00:00
   DSS-54_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-54_XYZ        =    ( +4849.434488     -360.7238999   +4114.618835 )
   DSS-54_DXYZ       =    (    -0.0100          0.0242          0.0156 )
   DSS-54_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-54_UP         =       'Z'
   DSS-54_NORTH      =       'X'
 
 
   SITES            +=      'DSS-55'
   DSS-55_FRAME      =       'EARTH_FIXED'
   DSS-55_CENTER     =       399
   DSS-55_IDCODE     =       399055
   DSS-55_EPOCH      =       @2003-JAN-01/00:00
   DSS-55_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-55_XYZ        =    ( +4849.525256     -360.6060932   +4114.495084 )
   DSS-55_DXYZ       =    (    -0.0100          0.0242          0.0156   )
   DSS-55_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-55_UP         =       'Z'
   DSS-55_NORTH      =       'X'
 
 
   SITES            +=      'DSS-56'
   DSS-56_FRAME      =       'EARTH_FIXED'
   DSS-56_CENTER     =       399
   DSS-56_IDCODE     =       399056
   DSS-56_EPOCH      =       @2003-JAN-01/00:00
   DSS-56_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-56_XYZ        =    ( +4849.421679     -360.549659    +4114.646987 )
   DSS-56_DXYZ       =    (    -0.0100          0.0242          0.0156   )
   DSS-56_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-56_UP         =       'Z'
   DSS-56_NORTH      =       'X'
 
 
   SITES            +=      'DSS-63'
   DSS-63_FRAME      =       'EARTH_FIXED'
   DSS-63_CENTER     =       399
   DSS-63_IDCODE     =       399063
   DSS-63_EPOCH      =       @2003-JAN-01/00:00
   DSS-63_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-63_XYZ        =    ( +4849.092518     -360.1803480   +4115.109251 )
   DSS-63_DXYZ       =    (    -0.0100          0.0242          0.0156   )
   DSS-63_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-63_UP         =       'Z'
   DSS-63_NORTH      =       'X'
 
 
   SITES            +=      'DSS-65'
   DSS-65_FRAME      =       'EARTH_FIXED'
   DSS-65_CENTER     =       399
   DSS-65_IDCODE     =       399065
   DSS-65_EPOCH      =       @2003-JAN-01/00:00
   DSS-65_BOUNDS     =    (  @1950-JAN-01/00:00,  @2150-JAN-01/00:00  )
   DSS-65_XYZ        =    ( +4849.339634     -360.4276637   +4114.750733 )
   DSS-65_DXYZ       =    (    -0.0100          0.0242          0.0156   )
   DSS-65_TOPO_EPOCH =       @2026-JUL-17/00:00
   DSS-65_UP         =       'Z'
   DSS-65_NORTH      =       'X'
 
begintext
 
begintext
 
[End of definitions file]
 
