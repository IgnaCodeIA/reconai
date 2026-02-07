import cv2

C_LINE = (0, 255, 0)
C_TORSO = (0, 255, 255)
C_POINT = (0, 0, 255)
C_FOOT = (0, 0, 255)
C_TEXT_OK = (0, 255, 0)
C_TEXT_WARN = (0, 0, 255)
C_INFO = (255, 0, 0)

def _p(lm, name, w, h):
    x, y = lm[name][0], lm[name][1]
    return int(x * w), int(y * h)

def draw_legacy_overlay(image_bgr, lm: dict, w: int, h: int, angles: dict,
                        a_max: float = 60.0, sequence: int = None, 
                        frame_idx: int = None, fps: int = None):
    need = [
        "RIGHT_HIP", "RIGHT_KNEE", "RIGHT_ANKLE",
        "LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE",
        "RIGHT_SHOULDER", "RIGHT_ELBOW", "RIGHT_WRIST",
        "LEFT_SHOULDER", "LEFT_ELBOW", "LEFT_WRIST",
        "RIGHT_HEEL", "RIGHT_FOOT_INDEX", "LEFT_HEEL", "LEFT_FOOT_INDEX",
    ]
    if any(k not in lm for k in need):
        if sequence is not None:
            cv2.rectangle(image_bgr, (15, 5), (250, 40), (250, 250, 250), -1)
            cv2.putText(image_bgr, f'Secuencia: {sequence}', (20, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, C_INFO, 1, cv2.LINE_AA)
        return image_bgr

    SH_R = _p(lm, "RIGHT_SHOULDER", w, h)
    EL_R = _p(lm, "RIGHT_ELBOW", w, h)
    WR_R = _p(lm, "RIGHT_WRIST", w, h)

    SH_L = _p(lm, "LEFT_SHOULDER", w, h)
    EL_L = _p(lm, "LEFT_ELBOW", w, h)
    WR_L = _p(lm, "LEFT_WRIST", w, h)

    HIP_R = _p(lm, "RIGHT_HIP", w, h)
    KN_R  = _p(lm, "RIGHT_KNEE", w, h)
    AN_R  = _p(lm, "RIGHT_ANKLE", w, h)

    HIP_L = _p(lm, "LEFT_HIP", w, h)
    KN_L  = _p(lm, "LEFT_KNEE", w, h)
    AN_L  = _p(lm, "LEFT_ANKLE", w, h)

    HE_R  = _p(lm, "RIGHT_HEEL", w, h)
    FI_R  = _p(lm, "RIGHT_FOOT_INDEX", w, h)
    HE_L  = _p(lm, "LEFT_HEEL", w, h)
    FI_L  = _p(lm, "LEFT_FOOT_INDEX", w, h)

    cv2.line(image_bgr, HIP_R, KN_R, C_LINE, 2)
    cv2.line(image_bgr, KN_R, AN_R, C_LINE, 2)
    cv2.circle(image_bgr, HIP_R, 5, C_POINT, -1)
    cv2.circle(image_bgr, KN_R, 5, C_POINT, -1)
    cv2.circle(image_bgr, AN_R, 5, C_POINT, -1)

    cv2.line(image_bgr, HIP_L, KN_L, C_LINE, 2)
    cv2.line(image_bgr, KN_L, AN_L, C_LINE, 2)
    cv2.circle(image_bgr, HIP_L, 5, C_POINT, -1)
    cv2.circle(image_bgr, KN_L, 5, C_POINT, -1)
    cv2.circle(image_bgr, AN_L, 5, C_POINT, -1)

    cv2.line(image_bgr, AN_R, HE_R, C_FOOT, 2)
    cv2.line(image_bgr, HE_R, FI_R, C_FOOT, 2)
    cv2.line(image_bgr, FI_R, AN_R, C_FOOT, 2)
    cv2.circle(image_bgr, HE_R, 5, C_POINT, -1)
    cv2.circle(image_bgr, FI_R, 5, C_POINT, -1)

    cv2.line(image_bgr, AN_L, HE_L, C_FOOT, 2)
    cv2.line(image_bgr, HE_L, FI_L, C_FOOT, 2)
    cv2.line(image_bgr, FI_L, AN_L, C_FOOT, 2)
    cv2.circle(image_bgr, HE_L, 5, C_POINT, -1)
    cv2.circle(image_bgr, FI_L, 5, C_POINT, -1)

    cv2.line(image_bgr, SH_R, EL_R, C_LINE, 2)
    cv2.line(image_bgr, EL_R, WR_R, C_LINE, 2)
    cv2.circle(image_bgr, SH_R, 5, C_POINT, -1)
    cv2.circle(image_bgr, EL_R, 5, C_POINT, -1)
    cv2.circle(image_bgr, WR_R, 5, C_POINT, -1)

    cv2.line(image_bgr, SH_L, EL_L, C_LINE, 2)
    cv2.line(image_bgr, EL_L, WR_L, C_LINE, 2)
    cv2.circle(image_bgr, SH_L, 5, C_POINT, -1)
    cv2.circle(image_bgr, EL_L, 5, C_POINT, -1)
    cv2.circle(image_bgr, WR_L, 5, C_POINT, -1)

    cv2.line(image_bgr, SH_R, SH_L, C_TORSO, 2)
    cv2.line(image_bgr, SH_L, HIP_L, C_TORSO, 2)
    cv2.line(image_bgr, HIP_L, HIP_R, C_TORSO, 2)
    cv2.line(image_bgr, HIP_R, SH_R, C_TORSO, 2)

    def _hline(center, half=200):
        x, y = center
        cv2.line(image_bgr, (x - half, y), (x + half, y), (100, 0, 255), 1)
    _hline(SH_R); _hline(SH_L); _hline(HIP_R); _hline(HIP_L)

    mid_sh = ((SH_R[0] + SH_L[0]) // 2, (SH_R[1] + SH_L[1]) // 2)
    mid_hp = ((HIP_R[0] + HIP_L[0]) // 2, (HIP_R[1] + HIP_L[1]) // 2)
    cv2.circle(image_bgr, mid_sh, 5, (0, 0, 255), -1)
    cv2.circle(image_bgr, mid_hp, 5, (0, 0, 255), -1)
    cv2.line(image_bgr, mid_sh, mid_hp, (255, 255, 0), 2)

    a_arm_r = angles.get("angle_arm_r")
    a_arm_l = angles.get("angle_arm_l")
    a_leg_r = angles.get("angle_leg_r")
    a_leg_l = angles.get("angle_leg_l")

    def _put(text, org, ok=True):
        cv2.putText(image_bgr, text, org, cv2.FONT_HERSHEY_SIMPLEX, 1, C_TEXT_OK if ok else C_TEXT_WARN, 2, cv2.LINE_AA)

    if a_arm_r is not None:
        _put(str(int(round(a_arm_r))), (EL_R[0] + 20, EL_R[1] + 20), ok=(a_arm_r >= a_max))
    if a_arm_l is not None:
        _put(str(int(round(a_arm_l))), (EL_L[0] + 20, EL_L[1] + 20), ok=True)
    if a_leg_r is not None:
        _put(str(int(round(a_leg_r))), (KN_R[0], KN_R[1]), ok=False)
    if a_leg_l is not None:
        _put(str(int(round(a_leg_l))), (KN_L[0], KN_L[1]), ok=False)

    cv2.rectangle(image_bgr, (15, 5), (250, 40), (250, 250, 250), -1)
    
    if sequence is not None:
        cv2.putText(image_bgr, f'Secuencia: {sequence}', (20, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, C_INFO, 1, cv2.LINE_AA)

    if frame_idx is not None or fps is not None:
        cv2.rectangle(image_bgr, (15, 45), (280, 95), (250, 250, 250), -1)
        
        y_pos = 70
        if frame_idx is not None:
            cv2.putText(image_bgr, f'Frame: {frame_idx}', (20, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, C_INFO, 1, cv2.LINE_AA)
            y_pos += 20
        
        if fps is not None:
            cv2.putText(image_bgr, f'{w}x{h} @ {fps}fps', (20, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, C_INFO, 1, cv2.LINE_AA)

    return image_bgr