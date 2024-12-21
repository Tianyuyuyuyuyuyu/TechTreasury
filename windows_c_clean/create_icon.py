from PIL import Image, ImageDraw, ImageFont
import os

def create_tyu_icon():
    size = 256
    padding = 20  # 内边距
    corner_radius = 50  # 圆角半径
    
    # 创建新图像
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制圆角矩形背景
    def rounded_rectangle(draw, rect, corner_radius, fill):
        """绘制圆角矩形"""
        x1, y1, x2, y2 = rect
        r = corner_radius
        
        # 绘制矩形主体
        draw.rectangle([x1+r, y1, x2-r, y2], fill=fill)
        draw.rectangle([x1, y1+r, x2, y2-r], fill=fill)
        
        # 绘制四个圆角
        draw.ellipse([x1, y1, x1+2*r, y1+2*r], fill=fill)  # 左上
        draw.ellipse([x2-2*r, y1, x2, y1+2*r], fill=fill)  # 右上
        draw.ellipse([x1, y2-2*r, x1+2*r, y2], fill=fill)  # 左下
        draw.ellipse([x2-2*r, y2-2*r, x2, y2], fill=fill)  # 右下
    
    # 绘制黑色背景
    rounded_rectangle(draw, 
                     [padding, padding, size-padding, size-padding],
                     corner_radius, 
                     fill=(0, 0, 0, 255))
    
    try:
        # 加载字体
        font_size = 100
        font = ImageFont.truetype("arial.ttf", font_size)
        
        # 计算文字位置
        text = "TYU"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # 居中绘制文字
        x = (size - text_width) // 2
        y = (size - text_height) // 2
        
        # 绘制文字（带简单抗锯齿效果）
        draw.text((x, y), text, 
                 fill=(255, 255, 255, 255),  # 纯白色
                 font=font)
        
    except Exception as e:
        print(f"添加文字时出错: {str(e)}")
    
    # 保存图标
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, 'cleaner.ico')
        
        # 保存多个尺寸的图标
        img.save(icon_path, format='ICO', 
                sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
        print(f"图标已成功保存到: {icon_path}")
        return icon_path
    except Exception as e:
        print(f"保存图标时出错: {str(e)}")
        return None

if __name__ == '__main__':
    create_tyu_icon() 