package com.suresh.srilankatv;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.provider.Settings;
import android.content.Context;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.GridLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.util.List;

/** Minimal Google TV channel home, designed for Xiaomi TV Box S 3rd Gen. */
public final class MainActivity extends Activity {
    private static final int BG=0xFF07101E;
    private static final int CARD=0xFF152439;
    private static final int FOCUS=0xFF39D8D0;
    private List<PlaylistStore.Channel> channels;
    private Button firstChannel;

    private int dp(float size) {return (int)(getResources().getDisplayMetrics().density*size+0.5f);}

    private GradientDrawable panel(boolean focused) {
        GradientDrawable background=new GradientDrawable();
        background.setColor(focused ? 0xFF21435A : CARD);
        background.setCornerRadius(dp(17));
        background.setStroke(dp(focused?3:1.2f),focused?FOCUS:0xFF28445C);
        return background;
    }

    private TextView text(String s,float sp,int color,boolean bold) {
        TextView v=new TextView(this);
        v.setText(s);
        v.setTextSize(sp);
        v.setTextColor(color);
        v.setGravity(Gravity.CENTER_VERTICAL);
        if (bold) v.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
        return v;
    }

    private void immersive() {
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().getDecorView().setSystemUiVisibility(5894 | 1024 | 512);
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
        immersive();
        channels=PlaylistStore.getChannels(this);
        draw();
    }

    @Override public void onResume() {
        super.onResume();
        immersive();
    }

    private void draw() {
        int screenDp=(int)(getResources().getDisplayMetrics().widthPixels/
            getResources().getDisplayMetrics().density);
        int cols=screenDp>=1050?5:screenDp>=730?4:screenDp>=490?3:2;
        int side=screenDp>=900?40:20;
        int cell=(screenDp-2*side-16)/cols;
        int cardWidth=cell-14;
        ScrollView scroller=new ScrollView(this);
        scroller.setClipToPadding(false);
        scroller.setFillViewport(true);
        scroller.setBackgroundColor(BG);
        scroller.setVerticalScrollBarEnabled(false);
        LinearLayout content=new LinearLayout(this);
        content.setPadding(dp(side),dp(14),dp(side),dp(25));
        content.setOrientation(LinearLayout.VERTICAL);
        scroller.addView(content);
        setContentView(scroller);

        LinearLayout header=new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        content.addView(header,new LinearLayout.LayoutParams(-1,dp(65)));
        TextView brand=text("TV",42,Color.WHITE,true);
        header.addView(brand,new LinearLayout.LayoutParams(0,-1,1));
        TextView hint=text("22 CHANNELS    •    SELECT WITH OK",14,0xFF849BB2,true);
        header.addView(hint);
        Button settings=new Button(this);
        settings.setText("⚙");
        settings.setTextSize(21);
        settings.setTextColor(0xFFB2C9DC);
        settings.setAllCaps(false);
        settings.setBackground(panel(false));
        LinearLayout.LayoutParams gearParams=new LinearLayout.LayoutParams(dp(58),dp(51));
        gearParams.leftMargin=dp(18);
        header.addView(settings,gearParams);
        settings.setOnClickListener(v->startActivity(new Intent(this,ShortcutHelpActivity.class)));
        settings.setOnFocusChangeListener((v,hasFocus)->settings.setBackground(panel(hasFocus)));

        TextView sub=text("Live TV    /    Your channels",16,0xFF93AFC5,false);
        LinearLayout.LayoutParams subParams=new LinearLayout.LayoutParams(-1,dp(43));
        content.addView(sub,subParams);

        GridLayout grid=new GridLayout(this);
        grid.setColumnCount(cols);
        grid.setUseDefaultMargins(false);
        grid.setPadding(0,0,0,dp(20));
        content.addView(grid);
        firstChannel=null;
        for (int i=0;i<channels.size();i++) {
            final int channelIndex=i;
            PlaylistStore.Channel ch=channels.get(i);

            // A single card is one focusable/clickable button for D-pad, mouse or touch.
            Button card=new Button(this);
            card.setAllCaps(false);
            card.setText(String.format(java.util.Locale.ROOT,"%02d   %s",i+1,ch.name));
            card.setTextSize(screenDp<750?14:16);
            card.setTextColor(0xFFF1F7FF);
            card.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
            card.setGravity(Gravity.CENTER);
            card.setPadding(dp(10),dp(12),dp(10),dp(12));
            card.setBackground(panel(false));
            card.setFocusable(true);
            card.setFocusableInTouchMode(true);
            card.setStateListAnimator(null);
            card.setSingleLine(false);
            card.setMaxLines(2);
            LogoLoader.attach(this,card,ch);
            card.setOnFocusChangeListener((v,focused)->{
                v.setBackground(panel(focused));
                v.setScaleX(focused?1.025f:1f);
                v.setScaleY(focused?1.025f:1f);
                v.setElevation(dp(focused?10:1));
            });
            card.setOnClickListener(v->{
                Intent player=new Intent(MainActivity.this,PlayerActivity.class);
                player.putExtra("channel_index",channelIndex);
                startActivity(player);
            });
            GridLayout.LayoutParams p=new GridLayout.LayoutParams();
            p.width=dp(cardWidth);
            p.height=dp(screenDp>=800?160:146);
            p.setMargins(dp(7),dp(7),dp(7),dp(7));
            grid.addView(card,p);
            if(firstChannel==null)firstChannel=card;
        }
        if(firstChannel!=null)firstChannel.requestFocus();
    }
}
