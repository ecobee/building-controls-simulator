from eppy import modeleditor
import argparse
import os

"""
This script 
1) fixes broken idf files
2) upgrades them to a new version if desired
"""

def add_surfProp(ep_idf):
    ep_idf.newidfobject(
        'SurfaceProperty:OtherSideCoefficients'.upper(),
        Name="SURFPROPOTHSDCOEFSLABAVERAGE",
        Combined_ConvectiveRadiative_Film_Coefficient=0,
        Ground_Temperature_Coefficient=1
    )
    ep_idf.newidfobject(
        'SurfaceProperty:OtherSideCoefficients'.upper(),
        Name="surfPropOthSdCoefBasementAvgFloor",
        Combined_ConvectiveRadiative_Film_Coefficient=0,
        Ground_Temperature_Coefficient=1
    )
    ep_idf.newidfobject(
        'SurfaceProperty:OtherSideCoefficients'.upper(),
        Name="surfPropOthSdCoefBasementAvgWall",
        Combined_ConvectiveRadiative_Film_Coefficient=0,
        Ground_Temperature_Coefficient=1
    )

def verify_r(ep_idf):
    idf_obj_name = "GroundHeatTransfer:Basement:Insulation".upper()
    if ep_idf.idfobjects[idf_obj_name]:
        if ep_idf.idfobjects[idf_obj_name][0].REXT_R_Value_of_any_exterior_insulation == 0:
            ep_idf.idfobjects[idf_obj_name][0].REXT_R_Value_of_any_exterior_insulation = 1.0


if __name__ == "__main__":
    print("=" * 80)
    print("EnergyPlus IDF preprocessor")
    print("=" * 80)
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, nargs="?",
                        help="input EnergyPlus .idf file to preprocess")
    parser.add_argument("-o", "--output", type=str, nargs="?",
                        help="ouput EnergyPlus .idf file")
    args = parser.parse_args()
    # config .idf file paths
    print("Runtime dir: {}".format(os.getcwd()))
    if args.input:
        idf_in_fname = args.input
        print("Input argument: {}".format(idf_in_fname))
    else:
        raise AttributeError((
            "Missing EnergyPlus input data file (idf) "
            "e.g. -i ../idf/ep_idf_file.idf"
        ))
    if args.output:
        idf_out_fname = args.output
        if not os.path.exists(os.path.dirname(idf_out_fname)):
            raise AttributeError((
                                     "Supplied output file name: {} "
                                     "is in a directory that does not exist."
                                 ).format(idf_out_fname))
    else:
        # default output fname, broken out from parser
        idf_out_fname = os.path.join(
            os.path.dirname(idf_in_fname),
            "test_output.idf"
        )

    # set file paths
    idf_in_path = os.path.join(os.getcwd(), idf_in_fname)
    idf_out_path = os.path.join(os.getcwd(), idf_out_fname)
    # set E+ IDD
    modeleditor.IDF.setiddname(os.environ["EPLUS_IDD"])
    print("Running with IDD: {}".format(modeleditor.IDF.iddname))

    # load .idf with eppy
    ep_idf = modeleditor.IDF(idf_in_path)
    print("loaded .idf file: {}".format(idf_in_path))
    verify_r(ep_idf)
    add_surfProp(ep_idf)
    ep_idf.saveas(idf_out_fname)
    print("Output: {}".format(idf_out_path))
