import pickle
import os
import torch
from transformers import RobertaTokenizer, RobertaForSequenceClassification, RobertaConfig

class DowntimeTypePredictor:
    """
    使用 RoBERTa 模型进行停机类型预测
    """
    
    def __init__(self, model_path=None):
        """
        初始化预测器
        
        参数:
        model_path (str): 模型文件路径
        """
        # 如果没有指定路径，使用脚本所在目录下的模型
        if model_path is None:
            # 获取当前脚本所在目录
            script_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(script_dir, 'roberta_downtime_model')
        
        self.model_path = model_path
        
        print(f"正在从本地加载模型: {model_path}")
        
        # 加载 tokenizer - 直接从本地文件加载
        self.tokenizer = RobertaTokenizer.from_pretrained(model_path)
        
        # 加载模型配置
        config = RobertaConfig.from_pretrained(model_path)
        
        # 加载模型 - 直接从本地文件加载
        self.model = RobertaForSequenceClassification.from_pretrained(
            model_path, 
            config=config
        )
        
        # 加载 label encoder
        with open(f'{model_path}/label_encoder.pkl', 'rb') as f:
            self.label_encoder = pickle.load(f)
        
        # 设置模型为评估模式
        self.model.eval()
        
        # 如果有 GPU，使用 GPU
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
    
    def predict(self, attraction_name, description):
        """
        预测停机类型
        
        参数:
        attraction_name (str): 设施名称
        description (str): 描述文本
        
        返回:
        dict: 包含预测结果的字典
        """
        # 组合文本
        text = f"{attraction_name} {description}"
        
        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors='pt',
            truncation=True,
            padding=True,
            max_length=512
        )
        
        # 将输入移动到设备
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # 预测
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
        
        # 获取预测类别
        predicted_class_id = torch.argmax(logits, dim=-1).item()
        predicted_class = self.label_encoder.inverse_transform([predicted_class_id])[0]
        
        # 获取概率
        probabilities = torch.softmax(logits, dim=-1)[0]
        confidence = probabilities[predicted_class_id].item()
        
        return {
            'predicted_class': predicted_class,
            'confidence': confidence,
            'probabilities': probabilities.cpu().numpy().tolist()
        }
