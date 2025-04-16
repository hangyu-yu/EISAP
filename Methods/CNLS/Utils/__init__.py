import os
import importlib.util
import types

# 创建一个空的ImpedanceFunctions模块对象
ImpedanceFunctions = types.ModuleType('ImpedanceFunctions')

# 获取当前包路径
package_path = os.path.dirname(__file__)

# 遍历所有子模块
for root, dirs, files in os.walk(package_path):
    if "__pycache__" in dirs:
        dirs.remove("__pycache__")
        
    for file in files:
        if file.endswith(".py") and not file.startswith("__"):
            # 构造模块路径
            module_path = os.path.join(root, file)
            module_name = os.path.splitext(file)[0]

            try:
                # 动态加载模块
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # 将模块中的函数添加到全局命名空间
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if callable(attr) and not attr_name.startswith("__"):
                        globals()[attr_name] = attr
                        
                        # 如果是来自ImpedanceFunctions.py的函数，添加到ImpedanceFunctions模块
                        if module_name == 'ImpedanceFunctions':
                            setattr(ImpedanceFunctions, attr_name, attr)
                
                # 如果是ImpedanceFunctions模块，将整个模块也存储起来
                if module_name == 'ImpedanceFunctions':
                    # 保留原始模块的文档字符串
                    if module.__doc__:
                        ImpedanceFunctions.__doc__ = module.__doc__
            
            except Exception as e:
                print(f"Error loading module {module_name}: {e}")

# 添加ImpedanceFunctions到__all__列表
__all__ = [name for name in globals() if callable(globals()[name]) and not name.startswith("__")]
__all__.append("ImpedanceFunctions")