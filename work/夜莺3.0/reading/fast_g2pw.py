"""g2pW 加速：替换其写死 2 线程的 ONNX 会话。"""
import os, onnxruntime
from g2pw import G2PWConverter


def make(model_dir, threads=8, providers=None):
    conv = G2PWConverter(model_dir=model_dir, style='pinyin', enable_non_tradional_chinese=True,
                         num_workers=0, batch_size=128)
    so = onnxruntime.SessionOptions()
    so.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
    so.intra_op_num_threads = threads
    conv.session_g2pw = onnxruntime.InferenceSession(os.path.join(model_dir, 'g2pw.onnx'), sess_options=so,
                                                     providers=providers or ['CPUExecutionProvider'])
    conv.num_workers = 0
    return conv
