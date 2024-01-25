import cv2
from PIL import ImageGrab, Image

# In this script, we will verify and draw the polygon bounding box
# we received from our OCI Vision API call.
example = [{'x': 0.3232421875, 'y': 0.3697916666666667},
            {'x': 0.458984375, 'y': 0.3697916666666667},
            {'x': 0.458984375, 'y': 0.6336805555555556},
            {'x': 0.3232421875, 'y': 0.6336805555555556}]

def draw_over_image(img, bb_normalized, label):

    img_h, img_w, _ = img.shape

    draw_color = (255, 255, 255)
    yellow = (128, 128, 0)
    green = (0, 255, 0)
    red = (255, 0, 0)
    white = (255, 255, 255)
    # format is: top left, top right, bottom right, bottom left.
    # to create a rectangle in opencv, we just need top left and bottom right. (pt1 and pt3)
    # we omit pt2 and pt4 from our calculations.
    (pt1, pt3) = (int(), int())

    pt1 = (bb_normalized[0]['x'] * img_w, bb_normalized[0]['y'] * img_h)
    pt3 = (bb_normalized[2]['x'] * img_w, bb_normalized[2]['y'] * img_h)

    draw_color = white

    img = cv2.rectangle(img=img, pt1=(int(pt1[0]), int(pt1[1])),
        pt2=(int(pt3[0]), int(pt3[1])),
        color=draw_color,
        thickness=5
    )

    cv2.putText(img, label, (int(pt3[0])+10, int(pt3[1])+10), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=draw_color, thickness=2
    )


    '''
    count = len(df[df['name']=='mask']) # detecting 'correct' mask class, for example.
    if (count) > 0:
        print('# Detections: {}'.format(count))
        CURRENT_DETECTIONS = count
    else:
        CURRENT_DETECTIONS = 0

    cv2.putText(img, 'Total Masks: {}'.format(CURRENT_DETECTIONS).upper(), (150, 150),
        cv2.FONT_HERSHEY_PLAIN, 2,
        white
    )
    '''

    return img



def main():
    
    img = cv2.imread('../img/22WHITEGOD1-superJumbo-v2.jpg')

    draw_result = draw_over_image(img, example, 'Dog')
    print(type(draw_result))
    cv2.imshow('Image', draw_result)

    im_rgb = cv2.cvtColor(draw_result, cv2.COLOR_BGR2RGB)
    pilImage = Image.fromarray(im_rgb)
    pilImage.save('../img/output_object_detection_verify.png', 'PNG')
    cv2.waitKey(1)


if __name__ == '__main__':
    main()