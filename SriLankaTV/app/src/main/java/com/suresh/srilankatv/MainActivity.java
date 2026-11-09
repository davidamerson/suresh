package com.suresh.srilankatv;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.text.TextWatcher;
import android.text.Editable;
import android.content.pm.ActivityInfo;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.GridLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.List;

public final class MainActivity extends Activity {
    private LinearLayout content;
    private List<PlaylistStore.Channel> channels;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,
                             WindowManager.LayoutParams.FLAG_FULLSCREEN);
        channels = PlaylistStore.getChannels(this);
        render();
        refreshRemote(false);
    }

    private int dp(int value) {
        return (int)(value * getResources().getDisplayMetrics().density + 0.5f);
    }

    private GradientDrawable shape(int background, int border) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(background);
        drawable.setCornerRadius(dp(11));
        drawable.setStroke(dp(2), border);
        return drawable;
    }

    private TextView label(String text, int sp, int color, boolean bold) {
        TextView v = new TextView(this);
        v.setText(text);
        v.setTextSize(sp);
        v.setTextColor(color);
        if (bold) v.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        v.setPadding(0, dp(7), 0, dp(7));
        return v;
    }

    private Button action(String name) {
        Button b = new Button(this);
        b.setText(name);
        b.setTextSize(17);
        b.setAllCaps(false);
        b.setTextColor(Color.WHITE);
        b.setMinHeight(dp(66));
        b.setBackground(shape(Color.rgb(26, 37, 56), Color.rgb(59, 83, 124)));
        b.setFocusable(true);
        b.setFocusableInTouchMode(true);
        b.setOnFocusChangeListener((view, focused) -> {
            b.setBackground(shape(
                focused ? Color.rgb(48, 80, 130) : Color.rgb(26, 37, 56),
                focused ? Color.rgb(255, 202, 69) : Color.rgb(59, 83, 124)));
            b.setScaleX(focused ? 1.05f : 1f);
            b.setScaleY(focused ? 1.05f : 1f);
        });
        return b;
    }

    private void showMessage(String message, boolean error) {
        TextView feedback = label(message, 16,
            error ? Color.rgb(255, 165, 160) : Color.rgb(170, 224, 177), false);
        content.addView(feedback);
    }

    private void render() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(Color.rgb(11, 19, 32));
        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(38), dp(24), dp(38), dp(28));
        scroll.addView(content);
        setContentView(scroll);

        boolean bridge = BuildConfig.FLAVOR.equals("sltvbridge");
        content.addView(label(bridge ? "SLTV CHANNEL BRIDGE" : "SRI LANKA TV INDEPENDENT", 30, Color.WHITE, true));
        content.addView(label(bridge
            ? "Live SLTV-hosted URLs • Requires server permission • Original SLTV fallback"
            : "Independent Android TV player • HLS/DASH • Remote control ready", 15,
            Color.rgb(169, 187, 210), false));
        boolean isCustom = PlaylistStore.usingCustom(this);
        content.addView(label(
            (isCustom ? "Imported list • " : "Observed sources (not all verified) • ")
            + channels.size() + " channels", 19, Color.rgb(255, 202, 69), true));


        if (bridge) {
            Button openOriginal = action("OPEN ORIGINAL SLTV APP");
            LinearLayout.LayoutParams linkParams = new LinearLayout.LayoutParams(dp(420),dp(70));
            content.addView(openOriginal,linkParams);
            openOriginal.setOnClickListener(v -> {
                try {
                    Intent launch = getPackageManager().getLaunchIntentForPackage("com.sltv.app");
                    if (launch != null) startActivity(launch);
                    else showMessage("Original SLTV is not installed, or is not visible to Android.",true);
                } catch(Exception ex) { showMessage("Could not open original SLTV",true); }
            });
            content.addView(label("No published SLTV channel deep-links were found. The button opens SLTV, not a selected channel. These hosted endpoints may return 403 in other apps.",14,Color.rgb(255,180,145),false));
        }
        Button sync = action("REFRESH CHANNEL CATALOGUE");
        content.addView(sync,new LinearLayout.LayoutParams(dp(420),dp(64)));
        sync.setOnClickListener(v -> refreshRemote(true));
        EditText search = new EditText(this);
        search.setSingleLine(true);
        search.setTextSize(17);
        search.setTextColor(Color.WHITE);
        search.setHintTextColor(Color.LTGRAY);
        search.setHint("Search channels / categories");
        content.addView(search,new LinearLayout.LayoutParams(dp(640),dp(70)));

        GridLayout grid = new GridLayout(this);
        grid.setColumnCount(3);
        grid.setPadding(dp(0), dp(8), dp(0), dp(12));
        Button first = null;
        for (int i = 0; i < channels.size(); i++) {
            final int index = i;
            PlaylistStore.Channel channel = channels.get(i);
            Button b = action((i + 1) + "   " + channel.name);
            GridLayout.LayoutParams lp = new GridLayout.LayoutParams();
            lp.width = dp(225);
            lp.height = dp(82);
            lp.setMargins(dp(8), dp(8), dp(8), dp(8));
            grid.addView(b, lp);
            b.setOnClickListener(view -> {
                Intent intent = new Intent(this, PlayerActivity.class);
                intent.putExtra("channel_index", index);
                startActivity(intent);
            });
            if (first == null) first = b;
        }
        content.addView(grid);
        search.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s,int st,int c,int a){}
            @Override public void onTextChanged(CharSequence q,int start,int before,int count) {
                String needle=q.toString().trim().toLowerCase(java.util.Locale.ROOT);
                for (int j=0;j<channels.size() && j<grid.getChildCount();j++) {
                    grid.getChildAt(j).setVisibility(channels.get(j).name.toLowerCase(java.util.Locale.ROOT)
                        .contains(needle)?View.VISIBLE:View.GONE);
                }
            }
            @Override public void afterTextChanged(Editable e){}
        });

        content.addView(label("ADD A PUBLIC M3U PLAYLIST", 19, Color.WHITE, true));
        content.addView(label("Optional: enter a public http/https M3U address to replace the starter channels. "
            + "No paid accounts, DRM bypass or subscription credentials.", 14,
            Color.rgb(175, 187, 205), false));

        EditText address = new EditText(this);
        address.setSingleLine(true);
        address.setTextColor(Color.WHITE);
        address.setHintTextColor(Color.rgb(164, 173, 193));
        address.setTextSize(16);
        address.setHint("https://example.com/my-public-channels.m3u");
        address.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        address.setBackground(shape(Color.rgb(27, 38, 58), Color.rgb(90, 111, 148)));
        address.setPadding(dp(18), dp(15), dp(18), dp(15));
        LinearLayout.LayoutParams inputLayout = new LinearLayout.LayoutParams(
            Math.min(dp(750), getResources().getDisplayMetrics().widthPixels - dp(100)), dp(68));
        inputLayout.topMargin = dp(10);
        content.addView(address, inputLayout);

        LinearLayout controls = new LinearLayout(this);
        controls.setOrientation(LinearLayout.HORIZONTAL);
        Button importBtn = action("Load M3U URL");
        Button restoreBtn = action("Restore starter list");
        LinearLayout.LayoutParams p1 = new LinearLayout.LayoutParams(dp(230), dp(70));
        p1.setMargins(0, dp(12), dp(20), dp(0));
        controls.addView(importBtn, p1);
        controls.addView(restoreBtn, new LinearLayout.LayoutParams(dp(265), dp(70)));
        content.addView(controls);

        importBtn.setOnClickListener(view -> {
            String url = address.getText().toString().trim();
            if (!url.startsWith("https://") && !url.startsWith("http://")) {
                showMessage("Please enter a public http:// or https:// playlist URL.", true);
                return;
            }
            importBtn.setEnabled(false);
            new Thread(() -> {
                try {
                    HttpURLConnection connection =
                        (HttpURLConnection)new URL(url).openConnection();
                    connection.setConnectTimeout(12000);
                    connection.setReadTimeout(12000);
                    connection.setRequestProperty("User-Agent", "SriLankaTV/0.1");
                    String text;
                    try {
                        text = PlaylistStore.readAll(connection.getInputStream());
                    } finally {
                        connection.disconnect();
                    }
                    List<PlaylistStore.Channel> parsed = PlaylistStore.parse(text);
                    if (parsed.isEmpty()) throw new IOException("No channel URLs in M3U");
                    runOnUiThread(() -> {
                        PlaylistStore.saveCustom(this, text);
                        channels = parsed;
                        render();
                    });
                } catch (Exception ex) {
                    runOnUiThread(() -> {
                        importBtn.setEnabled(true);
                        showMessage("Playlist unavailable: " + ex.getMessage(), true);
                    });
                }
            }).start();
        });
        restoreBtn.setOnClickListener(view -> {
            PlaylistStore.clearCustom(this);
            channels = PlaylistStore.getChannels(this);
            render();
        });
        content.addView(label("OK: select • D-pad: move • Back: return • During playback: "
            + "Up/Down change channel", 14, Color.rgb(169, 187, 210), false));

        if (first != null) first.requestFocus();
    }
    private void refreshRemote(boolean userRequested) {
        new Thread(() -> {
            try {
                List<PlaylistStore.Channel> updated=PlaylistStore.refresh(this);
                runOnUiThread(() -> {
                    channels=updated;
                    if (userRequested) render();
                });
            } catch(Exception ex) {
                if (userRequested) runOnUiThread(() -> showMessage("Remote catalogue unavailable. Saved channel list retained.",true));
            }
        }).start();
    }

}
