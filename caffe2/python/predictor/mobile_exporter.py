## @package mobile_exporter
# Module caffe2.python.mobile_exporter

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from caffe2.python import core, utils
from caffe2.proto import caffe2_pb2


def Export(workspace, net, params):
    """Returns init_net and predict_net suitable for writing to disk
       and loading into a Predictor"""
    proto = net if isinstance(net, caffe2_pb2.NetDef) else net.Proto()
    predict_net = caffe2_pb2.NetDef()
    predict_net.CopyFrom(proto)
    init_net = caffe2_pb2.NetDef()
    # Populate the init_net.
    ssa, blob_versions = core.get_ssa(net)
    inputs = []
    for versioned_inputs, _ in ssa:
        inputs += [name for name, _ in versioned_inputs]

    input_blobs = [blob_name for blob_name, version in
                   blob_versions.items()
                   if version == 0 and blob_name not in params]
    # Blobs that are never used as an input to another layer,
    # i.e. strictly output blobs.
    output_blobs = [blob_name for blob_name, version in
                    blob_versions.items()
                    if version != 0 and blob_name not in inputs]

    for blob_ref in params:
        blob_name = str(blob_ref)
        blob = workspace.FetchBlob(blob_name)
        init_net.op.extend(
            [
                core.CreateOperator(
                    "GivenTensorFill", [], [blob_name],
                    arg=[
                        utils.MakeArgument("shape", blob.shape),
                        utils.MakeArgument("values", blob)
                    ]
                )
            ]
        )
    # We have to make sure the blob exists in the namespace
    # and we can do so with fake data. (Which is immediately overwritten
    # by any typical usage)
    for blob_name in input_blobs:
        init_net.op.extend(
            [
                core.CreateOperator(
                    "GivenTensorFill", [], [blob_name],
                    arg=[
                        utils.MakeArgument("shape", [1, 1]),
                        utils.MakeArgument("values", [0.0])
                    ]
                )
            ]
        )

    # Now we make input/output_blobs line up with what Predictor expects.
    del predict_net.external_input[:]
    predict_net.external_input.extend(input_blobs)
    # For populating weights
    predict_net.external_input.extend(proto.external_input)
    # Ensure the output is also consistent with what we want
    del predict_net.external_output[:]
    predict_net.external_output.extend(output_blobs)
    return init_net, predict_net
