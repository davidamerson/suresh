package lk.openstream.tv.common;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AbsListView;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.BaseAdapter;
import android.widget.EditText;
import android.widget.GridView;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.TextView;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;

public abstract class TvMenuActivity extends Activity {
    private static final int BG=Color.rgb(13,19,32),PANEL=Color.rgb(26,37,57),ACCENT=Color.rgb(51,176,223);
    private final List<Channel> all=new ArrayList<>(),visible=new ArrayList<>();
    private final List<String> categories=new ArrayList<>();
    private ListView categoryList;
    private GridView channelGrid;
    private ChannelAdapter adapter;
    private EditText search;
    private TextView summary,heading;
    private String selected="All channels";
    protected abstract void openChannel(Channel ch);
    protected abstract String appTitle();
    protected abstract String appSubtitle();

    private int dp(float v){return Math.round(getResources().getDisplayMetrics().density*v);}
    private GradientDrawable shape(int color,int stroke){
        GradientDrawable d=new GradientDrawable();
        d.setColor(color);d.setCornerRadius(dp(12));
        if(stroke!=0)d.setStroke(dp(2),stroke);
        return d;
    }
    private TextView label(String text,int sp,boolean bold,int color){
        TextView v=new TextView(this);v.setText(text);
        v.setTextSize(sp);v.setTextColor(color);
        v.setGravity(Gravity.CENTER_VERTICAL);
        if(bold)v.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
        return v;
    }
    @Override public void onCreate(Bundle b){
        super.onCreate(b);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            |View.SYSTEM_UI_FLAG_FULLSCREEN|View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
            |View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        LinearLayout root=new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);root.setPadding(dp(20),dp(14),dp(20),dp(14));
        root.setBackgroundColor(BG);setContentView(root);
        heading=label(appTitle(),27,true,Color.WHITE);
        root.addView(heading,new LinearLayout.LayoutParams(-1,dp(40)));
        summary=label(appSubtitle(),13,false,Color.rgb(164,184,208));
        root.addView(summary,new LinearLayout.LayoutParams(-1,dp(29)));
        LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);
        root.addView(row,new LinearLayout.LayoutParams(-1,0,1));
        categoryList=new ListView(this);
        categoryList.setBackground(shape(PANEL,0));
        categoryList.setDivider(null);
        categoryList.setPadding(dp(5),dp(5),dp(5),dp(5));
        row.addView(categoryList,new LinearLayout.LayoutParams(dp(220),-1));
        LinearLayout right=new LinearLayout(this);right.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams rightP=new LinearLayout.LayoutParams(0,-1,1);
        rightP.leftMargin=dp(16);row.addView(right,rightP);
        search=new EditText(this);search.setSingleLine(true);
        search.setHint("Search all TV channels…");
        search.setTextColor(Color.WHITE);search.setHintTextColor(Color.rgb(148,164,185));
        search.setTextSize(15);search.setPadding(dp(16),0,dp(16),0);
        search.setBackground(shape(PANEL,0));
        right.addView(search,new LinearLayout.LayoutParams(-1,dp(46)));
        channelGrid=new GridView(this);
        channelGrid.setNumColumns(4);
        channelGrid.setVerticalSpacing(dp(10));channelGrid.setHorizontalSpacing(dp(10));
        channelGrid.setPadding(0,dp(12),0,0);channelGrid.setClipToPadding(false);
        channelGrid.setSelector(android.R.color.transparent);
        adapter=new ChannelAdapter();channelGrid.setAdapter(adapter);
        right.addView(channelGrid,new LinearLayout.LayoutParams(-1,0,1));
        channelGrid.setOnItemClickListener((parent,view,position,id)->{
            if(position>=0&&position<visible.size())openChannel(visible.get(position));
        });
        search.addTextChangedListener(new TextWatcher(){
            public void beforeTextChanged(CharSequence s,int st,int count,int aft){}
            public void onTextChanged(CharSequence s,int start,int before,int count){filter();}
            public void afterTextChanged(Editable e){}
        });
        categoryList.setOnItemClickListener((p,v,pos,id)->{
            if(pos<categories.size()){selected=categories.get(pos);filter();}
        });
        Catalog.load(this,(list,refreshed)->{
            all.clear();all.addAll(list);
            categories.clear();categories.add("All channels");
            categories.add("Public candidates");
            LinkedHashSet<String> catSet=new LinkedHashSet<>();
            catSet.add("SL Channels 🇱🇰");catSet.add("🇱🇰 Ultra");catSet.add("🇱🇰 Channels Ultra");
            for(Channel ch:all)catSet.add(ch.category);
            categories.addAll(catSet);
            ArrayAdapter<String> categoryAdapter=new ArrayAdapter<String>(
                this,android.R.layout.simple_list_item_1,categories){
                @Override public View getView(int pos,View convert,ViewGroup parent){
                    TextView v=label(getItem(pos),14,pos==categories.indexOf(selected),Color.WHITE);
                    v.setPadding(dp(12),dp(8),dp(7),dp(8));
                    v.setBackground(shape(categories.get(pos).equals(selected)?Color.rgb(29,90,129):PANEL,0));
                    v.setFocusable(true);v.setOnFocusChangeListener((view,focus)->{
                        view.setBackground(shape(focus?Color.rgb(40,105,141):
                            categories.get(pos).equals(selected)?Color.rgb(29,90,129):PANEL,
                            focus?ACCENT:0));
                    });return v;
                }
            };
            categoryList.setAdapter(categoryAdapter);
            summary.setText(all.size()+" channels  •  "+(refreshed?"online catalogue refreshed":"cached catalogue")+
                "  •  D-pad to select");
            filter();if(!refreshed)channelGrid.requestFocus();
        });
    }
    private void filter(){
        visible.clear();String term=search.getText().toString().toLowerCase(Locale.ROOT);
        for(Channel c:all){
            if(!selected.equals("All channels") &&
                !(selected.equals("Public candidates")&&c.canPlayDirectly()) &&
                !selected.equals(c.category))continue;
            if(!c.name.toLowerCase(Locale.ROOT).contains(term))continue;
            visible.add(c);
        }
        adapter.notifyDataSetChanged();
        if(channelGrid!=null)channelGrid.setSelection(0);
    }
    private final class ChannelAdapter extends BaseAdapter {
        @Override public int getCount(){return visible.size();}
        @Override public Object getItem(int p){return visible.get(p);}
        @Override public long getItemId(int p){return p;}
        @Override public View getView(int pos,View reuse,ViewGroup parent){
            Channel ch=visible.get(pos);
            LinearLayout item=new LinearLayout(TvMenuActivity.this);
            item.setOrientation(LinearLayout.VERTICAL);item.setPadding(dp(12),dp(9),dp(8),dp(7));
            item.setBackground(shape(PANEL,0));
            item.setMinimumHeight(dp(90));item.setFocusable(true);
            TextView name=label(ch.name,15,true,Color.WHITE);name.setMaxLines(2);
            item.addView(name,new LinearLayout.LayoutParams(-1,0,1));
            String status=ch.canPlayDirectly()?"▶ STREAM":ch.access.equals("sltv_backend")?"SLTV SERVER":
                ch.access.equals("provider_restricted")?"RESTRICTED":"UNVERIFIED";
            TextView sub=label(status,10,false,
                ch.canPlayDirectly()?Color.rgb(100,224,165):Color.rgb(166,189,208));
            item.addView(sub,new LinearLayout.LayoutParams(-1,dp(19)));
            item.setOnFocusChangeListener((v,focus)->{
                item.setBackground(shape(focus?Color.rgb(37,83,113):PANEL,focus?ACCENT:0));
                item.setScaleX(focus?1.015f:1f);item.setScaleY(focus?1.015f:1f);
            });
            item.setLayoutParams(new AbsListView.LayoutParams(-1,dp(96)));
            return item;
        }
    }
}
