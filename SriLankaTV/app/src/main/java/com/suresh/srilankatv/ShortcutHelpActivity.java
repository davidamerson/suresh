package com.suresh.srilankatv;

import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.provider.Settings;
import android.view.View;
import android.view.Gravity;
import android.view.WindowManager;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.widget.TextView;
import android.widget.LinearLayout;
import android.widget.Button;

/** Short, opt-in explanation: Xiaomi's stock Prime key is vendor-controlled. */
public final class ShortcutHelpActivity extends Activity {
    private int dp(float v){return (int)(v*getResources().getDisplayMetrics().density+.5f);}
    private TextView label(String value,int size,int color){
        TextView t=new TextView(this);
        t.setText(value);
        t.setTextSize(size);
        t.setTextColor(color);
        t.setPadding(dp(12),dp(6),dp(12),dp(8));
        return t;
    }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
        LinearLayout root=new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER);
        root.setBackgroundColor(0xFF071625);
        root.setPadding(dp(70),dp(22),dp(70),dp(25));
        setContentView(root);
        root.addView(label("TV  /  Prime Video remote button",30,Color.WHITE));
        root.addView(label("Your Xiaomi TV Box S (3rd Gen) remote may send BUTTON_7 (scan code 207) when Prime Video is pressed.",17,0xFFB9CFE2));
        root.addView(label("Optional: enable the 'TV Prime button shortcut' in Accessibility settings. Our service listens only for that shortcut and opens TV. It does not change system files.",17,0xFFB9CFE2));
        root.addView(label("Important: Some firmware intercepts dedicated app buttons before accessibility services. This shortcut cannot be guaranteed on every Xiaomi update.",15,0xFFF2C98D));
        Button open=new Button(this);
        open.setText("OPEN ACCESSIBILITY SETTINGS");
        open.setTextColor(Color.WHITE);
        open.setAllCaps(false);
        open.setTextSize(17);
        root.addView(open,new LinearLayout.LayoutParams(dp(410),dp(74)));
        open.setOnClickListener(v->startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)));
        Button back=new Button(this);
        back.setText("BACK TO TV");
        back.setTextColor(Color.WHITE);
        back.setAllCaps(false);
        root.addView(back,new LinearLayout.LayoutParams(dp(270),dp(65)));
        back.setOnClickListener(v->finish());
        open.requestFocus();
    }
}