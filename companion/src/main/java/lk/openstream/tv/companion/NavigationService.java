package lk.openstream.tv.companion;

import android.accessibilityservice.AccessibilityService;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import java.util.ArrayDeque;
import java.util.Locale;

public class NavigationService extends AccessibilityService {
    private long lastAction=0L;
    private String lastSearch="";
    private int scrollCount=0;

    private String normalize(String str){
        if(str==null)return "";
        return str.replaceAll("[\\u200B-\\u200F\\uFEFF]","")
           .replace("‎","").replace("²","").trim().toLowerCase(Locale.ROOT)
           .replaceAll("[^\\p{L}\\p{N}]+"," ").trim();
    }
    private boolean click(AccessibilityNodeInfo n){
        AccessibilityNodeInfo p=n;
        for(int i=0;i<5 && p!=null;i++){
            if(p.isClickable() && p.performAction(AccessibilityNodeInfo.ACTION_CLICK))return true;
            p=p.getParent();
        }
        return false;
    }
    private AccessibilityNodeInfo findExact(AccessibilityNodeInfo root,String wanted){
        if(root==null)return null;
        ArrayDeque<AccessibilityNodeInfo> q=new ArrayDeque<>();q.add(root);
        int visits=0;
        while(!q.isEmpty()&&visits++<500){
            AccessibilityNodeInfo n=q.removeFirst();
            String title=n.getContentDescription()!=null?n.getContentDescription().toString():
                         n.getText()!=null?n.getText().toString():"";
            if(!title.isEmpty()&&normalize(title).equals(normalize(wanted)))return n;
            for(int i=0;i<n.getChildCount();i++) {
                AccessibilityNodeInfo ch=n.getChild(i);
                if(ch!=null)q.add(ch);
            }
        }
        return null;
    }
    private AccessibilityNodeInfo findByClass(AccessibilityNodeInfo root,String cls){
        if(root==null)return null;
        ArrayDeque<AccessibilityNodeInfo> q=new ArrayDeque<>();q.add(root);
        int visits=0;
        while(!q.isEmpty()&&visits++<500){
            AccessibilityNodeInfo n=q.removeFirst();
            if(n.getClassName()!=null&&cls.equals(n.getClassName().toString()))return n;
            for(int i=0;i<n.getChildCount();i++){
                AccessibilityNodeInfo ch=n.getChild(i);if(ch!=null)q.add(ch);
            }
        }
        return null;
    }
    private AccessibilityNodeInfo findScrollable(AccessibilityNodeInfo root){
        if(root==null)return null;
        ArrayDeque<AccessibilityNodeInfo> q=new ArrayDeque<>();q.add(root);
        while(!q.isEmpty()){
            AccessibilityNodeInfo n=q.removeFirst();
            if(n.isScrollable())return n;
            for(int i=0;i<n.getChildCount();i++){
                AccessibilityNodeInfo ch=n.getChild(i);if(ch!=null)q.add(ch);
            }
        }
        return null;
    }
    @Override public void onAccessibilityEvent(AccessibilityEvent event){
        if(event.getPackageName()==null ||
           !"com.sltv.app".contentEquals(event.getPackageName()))return;
        SharedPreferences prefs=getSharedPreferences("sltv_navigation",Context.MODE_PRIVATE);
        String target=prefs.getString("target_channel","");
        long requested=prefs.getLong("requested_at",0);
        if(target.isEmpty())return;
        if(System.currentTimeMillis()-requested>120000){
            prefs.edit().remove("target_channel").remove("requested_at").apply();return;
        }
        long now=SystemClock.uptimeMillis();
        if(now-lastAction<800)return;
        AccessibilityNodeInfo root=getRootInActiveWindow();if(root==null)return;
        // Only interact with the original SLTV foreground interface. No network interception.
        AccessibilityNodeInfo channel=findExact(root,target);
        if(channel!=null&&click(channel)){
            prefs.edit().remove("target_channel").remove("requested_at").apply();
            lastSearch="";scrollCount=0;lastAction=now;return;
        }
        AccessibilityNodeInfo skip=findExact(root,"මඟහරින්න");
        if(skip==null)skip=findExact(root,"Skip");
        if(skip!=null&&click(skip)){lastAction=now;return;}
        // SLTV exposes a channel search box via Flutter accessibility semantics.
        AccessibilityNodeInfo search=findByClass(root,"android.widget.EditText");
        if(search!=null&&!target.equals(lastSearch)){
            Bundle b=new Bundle();
            b.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,target);
            if(search.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,b)){
                lastSearch=target;lastAction=now;return;
            }
        }
        AccessibilityNodeInfo scroll=findScrollable(root);
        if(scroll!=null&&scrollCount++<24&&scroll.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)){
            lastAction=now;
        }
    }
    @Override public void onInterrupt(){}
}
