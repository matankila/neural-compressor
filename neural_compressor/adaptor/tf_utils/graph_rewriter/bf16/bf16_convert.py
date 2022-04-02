#
#  -*- coding: utf-8 -*-
#
#  Copyright (c) 2021 Intel Corporation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import copy
from tensorflow.core.framework import attr_value_pb2
from tensorflow.python.framework import dtypes
from tensorflow.python.framework import tensor_util
from tensorflow.python.framework import op_def_registry
from tensorflow.python.framework.kernels import get_registered_kernels_for_op

from ..graph_base import GraphRewriterBase
from ..graph_util import GraphAnalyzer
from ..graph_util import GraphRewriterHelper as Helper

DT_FLOAT32  = attr_value_pb2.AttrValue(type=dtypes.float32.as_datatype_enum)
DT_BFLOAT16 = attr_value_pb2.AttrValue(type=dtypes.bfloat16.as_datatype_enum)

class BF16Convert(GraphRewriterBase):
    """
    BF16 node convert transformation.
    """
    def __init__(self,
                 model,
                 fp32_ops=[],
                 bf16_ops=[]):
        super().__init__(model)

        self.cur_graph = GraphAnalyzer()
        self.cur_graph.graph = self.model
        self.fp32_ops = fp32_ops
        self.bf16_ops = bf16_ops
        self.converted_ops = []
        self.device = "CPU"  #TODO support differnt device type

    def _dtype(self, node):
        op_def = op_def_registry.get(node.op)
        inputs_dt = []
        outputs_dt = []
        for i in op_def.input_arg:
            inputs_num = node.attr[i.number_attr].i if i.number_attr else 1
            for j in range(inputs_num):
                if i.type:
                    inputs_dt.append('')
                else:
                    inputs_dt.append(i.type_attr)
        for i in op_def.output_arg:
            outputs_num = node.attr[i.number_attr].i if i.number_attr else 1
            for j in range(outputs_num):
                if i.type:
                    outputs_dt.append('')
                else:
                    outputs_dt.append(i.type_attr)
        return inputs_dt, outputs_dt

    def _dtype_val(self, node):
        op_def = op_def_registry.get(node.op)
        inputs_dt_val = []
        outputs_dt_val = []
        for i in op_def.input_arg:
            inputs_num = node.attr[i.number_attr].i if i.number_attr else 1
            for j in range(inputs_num):
                if i.type:
                    inputs_dt_val.append(copy.deepcopy(attr_value_pb2.AttrValue(type=i.type)))
                else:
                    inputs_dt_val.append(copy.deepcopy(node.attr[i.type_attr]))
        for i in op_def.output_arg:
            outputs_num = node.attr[i.number_attr].i if i.number_attr else 1
            for j in range(outputs_num):
                if i.type:
                    outputs_dt_val.append(copy.deepcopy(attr_value_pb2.AttrValue(type=i.type)))
                else:
                    outputs_dt_val.append(copy.deepcopy(node.attr[i.type_attr]))
        return inputs_dt_val, outputs_dt_val

    def _allowed_dtype_val(self, node):
        op_def = op_def_registry.get(node.op)
        allowed_dt_val = {}
        for attr_def in op_def.attr:
            if attr_def.type != "type":
              continue
            if attr_def.HasField("allowed_values"):
                allowed_dt_val[attr_def.name] = attr_def.allowed_values.list.type
        # The supported data type in op_def may be different with registered kernels.
        # Use the registered one if exists.
        registered_dt_val = {}
        registered_kernels = get_registered_kernels_for_op(node.op)
        for kernel in registered_kernels.kernel:
            if kernel.device_type == self.device:
                for constraint in kernel.constraint:
                    if constraint.name in allowed_dt_val and constraint.HasField("allowed_values"):
                        if constraint.name not in registered_dt_val:
                            registered_dt_val[constraint.name] = constraint.allowed_values.list.type
                        else:
                            registered_dt_val[constraint.name].extend(constraint.allowed_values.list.type)
        for dt_val in registered_dt_val:
            if registered_dt_val[dt_val] != [] and dt_val in allowed_dt_val:
                allowed_dt_val[dt_val] = registered_dt_val[dt_val]
        return allowed_dt_val

    def _bf16_convert(self, bf16_node_name):
        bf16_node_detail = self.cur_graph.node_name_details[bf16_node_name]
        bf16_node = bf16_node_detail.node
        bf16_node_outputs = copy.deepcopy(bf16_node_detail.outputs)

        if bf16_node.name in self.converted_ops:
            return
        elif 'Dequantize' in bf16_node.op:
            return
        else:
            self.converted_ops.append(bf16_node.name)

        inputs_dt, outputs_dt = self._dtype(bf16_node)
        inputs_dt_val, outputs_dt_val = self._dtype_val(bf16_node)
        allowed_dt_val = self._allowed_dtype_val(bf16_node)

        # skip bf16 node whose inputs are all not FP32 data type
        if all([True if i != DT_FLOAT32 else False for i in inputs_dt_val]):
            return

        for index, input_name in enumerate(bf16_node.input):
            if input_name.startswith('^'):
                continue

            input_detail = self.cur_graph.node_name_details[Helper.node_name_from_input(
                input_name)]
            input_node = input_detail.node
            input_node_outputs = input_detail.outputs

            #print(bf16_node.op, bf16_node.name, input_node.op, input_node.name, allowed_dt_val, inputs_dt[index])
            if inputs_dt[index] in allowed_dt_val and dtypes.bfloat16.as_datatype_enum not in allowed_dt_val[inputs_dt[index]]:
                continue

            if inputs_dt_val[index] != DT_FLOAT32:
                continue

            if input_node.op == 'Cast' and \
                 input_node.attr["SrcT"] == DT_BFLOAT16 and \
                 input_node.attr["DstT"] == DT_FLOAT32 and len(input_node_outputs) == 1:
                    parent_input_name = Helper.node_name_from_input(input_node.input[0])
                    bf16_node.input[index] = input_node.input[0]
                    outputs = self.cur_graph.node_name_details[parent_input_name].outputs
                    outputs = list(map(lambda x: x.replace(input_name, bf16_node.name), outputs))
                    self.cur_graph.remove_node(input_name)
            elif input_node.op == 'Cast' and \
                 input_node.attr["DstT"] == DT_FLOAT32 and len(input_node_outputs) == 1:
                input_node.attr["DstT"].CopyFrom(DT_BFLOAT16)
            elif input_node.op == "Const" and len(input_node_outputs) == 1:
                fp32_value = tensor_util.MakeNdarray(input_node.attr.get('value').tensor)
                Helper.set_attr_dtype(input_node, "dtype", dtypes.bfloat16)
                input_node.attr['value'].CopyFrom(attr_value_pb2.AttrValue(
                    tensor=tensor_util.make_tensor_proto(
                        fp32_value, dtypes.bfloat16, fp32_value.shape)))
            elif input_node.name in self.bf16_ops and "Dequantize" not in input_node.op:
                self._bf16_convert(input_node.name)
            else:
                cast_node_name = input_name.replace(':', '_') + "/" + bf16_node_name + "_FP32toBF16"
                assert cast_node_name not in list(self.cur_graph.node_name_details.keys())
                input_cast_node = Helper.create_node(
                    "Cast", cast_node_name, [input_name])
                Helper.set_attr_dtype(input_cast_node, "DstT", dtypes.bfloat16)
                Helper.set_attr_dtype(input_cast_node, "SrcT", dtypes.float32)
                Helper.set_attr_bool(input_cast_node, "Truncate", False)
                bf16_node.input[index] = input_cast_node.name
                outputs = self.cur_graph.node_name_details[ \
                                  Helper.node_name_from_input(input_name)].outputs
                outputs = list(map(lambda x: x.replace(bf16_node.name, cast_node_name), outputs))
                self.cur_graph.add_node(input_cast_node, input_name, [bf16_node_name])

            bf16_node.attr[inputs_dt[index]].CopyFrom(
                               attr_value_pb2.AttrValue(type=dtypes.bfloat16.as_datatype_enum))
        if all([True if i != DT_FLOAT32 else False for i in outputs_dt_val]):
            return

        for output_name in bf16_node_outputs:
            output_detail = self.cur_graph.node_name_details[output_name]
            output_node = output_detail.node
            inputs_dt_input_node, _ = self._dtype(output_node)
            allowed_output_node_dt_val = self._allowed_dtype_val(output_node)

            for i, input_name in enumerate(output_node.input):
                if input_name.startswith('^'):
                    continue

                if bf16_node.name != input_name.split(':')[0]:
                    continue

                index = int(input_name.split(':')[-1]) if ':' in input_name else 0
                if outputs_dt_val[index] != DT_FLOAT32:
                    continue

                if output_node.op == 'Cast':
                    output_node.attr["SrcT"].CopyFrom(DT_BFLOAT16)
                elif output_node.op == 'QuantizeV2' and 'dtype' in output_node.attr:
                    if 'dtype' in allowed_output_node_dt_val and \
                         dtypes.bfloat16.as_datatype_enum in allowed_output_node_dt_val['dtype']:
                        output_node.attr["dtype"].CopyFrom(DT_BFLOAT16)
                elif output_node.name not in self.bf16_ops or \
                         inputs_dt_input_node[i] in allowed_output_node_dt_val and \
                         dtypes.bfloat16.as_datatype_enum not in allowed_output_node_dt_val[inputs_dt_input_node[i]]:
                    cast_node_name = bf16_node_name + "/" + output_node.name + "_BF16toFP32"
                    assert cast_node_name not in list(self.cur_graph.node_name_details.keys())
                    output_cast_node = Helper.create_node(
                        "Cast", cast_node_name, [input_name])
                    Helper.set_attr_dtype(output_cast_node, "DstT", dtypes.float32)
                    Helper.set_attr_dtype(output_cast_node, "SrcT", dtypes.bfloat16)
                    Helper.set_attr_bool(output_cast_node, "Truncate", False)
                    index = [i for i in output_node.input].index(input_name)
                    output_node.input[index] = output_cast_node.name
                    self.cur_graph.add_node(output_cast_node, bf16_node_name, [output_name])

    def _model_bf16_convert(self):
        logging.debug("start convert bf16 graph")
        self.cur_graph.parse_graph()
        for bf16_node_name in set(self.bf16_ops):
            if bf16_node_name not in self.cur_graph.node_name_details:
                self.bf16_ops.remove(bf16_node_name)
                continue
        for bf16_node_name in set(self.bf16_ops):
            self._bf16_convert(bf16_node_name)
        return self.cur_graph.dump_graph()

    def do_transformation(self):
        """
        Execute BF16 convert.
        :return: Transformed graph
        """
        converted_graph_def = self._model_bf16_convert()
        converted_graph_def.library.CopyFrom(self.model.library)
        return converted_graph_def
