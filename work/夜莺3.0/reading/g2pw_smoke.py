from g2pw import G2PWConverter

if __name__ == '__main__':
    conv = G2PWConverter(model_dir='models/G2PWModel/', style='pinyin',
                         enable_non_tradional_chinese=True, num_workers=0)
    S = ['他慢慢地走过来，心里觉得很高兴。', '我了解这个情况，你受不了就走吧。',
         '银行行长长得很高，头发很长。', '这件事还没还清，他还在睡觉。',
         '天气暖和，我和他一起和面，和了一把牌。', '他重新穿上厚重的衣服。']
    for s, r in zip(S, conv(S)):
        print(s, r)
