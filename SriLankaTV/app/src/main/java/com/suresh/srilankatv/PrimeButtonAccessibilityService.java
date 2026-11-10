package com.suresh.srilankatv;

import android.accessibilityservice.AccessibilityService;
import android.view.accessibility.AccessibilityEvent;
import android.view.KeyEvent;
import android.content.Intent;

/**
 * Optional user-enabled shortcut. Handles ONLY Xiaomi RC Prime Video BUTTON_7.
 * No root, no firmware modification, no watching UI content, no analytics.
 * Other keys and accessibility events are ignored.
 */
public final class PrimeButtonAccessibilityService extends AccessibilityService {
    @Override protected boolean onKeyEvent(KeyEvent event) {
        boolean prime=event.getKeyCode()==KeyEvent.KEYCODE_BUTTON_7 ||
            event.getScanCode()==207;
        if(!prime)return false;
        if(event.getAction()==KeyEvent.ACTION_DOWN &&
           event.getRepeatCount()==0) {
            Intent start=new Intent(this,MainActivity.class);
            start.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK |
                Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            startActivity(start);
        }
        return true;
    }
    @Override public void onAccessibilityEvent(AccessibilityEvent e) {}
    @Override public void onInterrupt() {}
}