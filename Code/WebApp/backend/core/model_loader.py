from ultralytics import YOLO #type: ignore
import xgboost as xgb #type: ignore
from core.config import (
    POSE_MODEL_PATH,
    OBJECT_MODEL_PATH,
    TROLLEY_MODEL_PATH,
    XGB_MODEL_PATH
)

class ModelLoader:
    pose_model = None
    object_model = None
    trolley_model = None
    xgb_model = None

    @classmethod
    def load_models(cls):
        if cls.pose_model is None:
            print("Loading YOLO Pose Model...")
            cls.pose_model = YOLO(POSE_MODEL_PATH)
        
        if cls.object_model is None:
            print("Loading YOLO Object Model...")
            cls.object_model = YOLO(OBJECT_MODEL_PATH)

        if cls.trolley_model is None:
            print("Loading YOLO Trolley Model...")
            cls.trolley_model = YOLO(TROLLEY_MODEL_PATH)

        if cls.xgb_model is None:
            print("Loading XGBoost Model...")
            cls.xgb_model = xgb.Booster()
            cls.xgb_model.load_model(XGB_MODEL_PATH)

        print("All Models Loaded Sucessfully !!")

    @classmethod
    def get_models(cls):
        return (
            cls.pose_model,
            cls.object_model,
            cls.trolley_model,
            cls.xgb_model
        )