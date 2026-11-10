package com.suresh.srilankatv;

import android.content.Context;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public final class PlaylistStore {
    private PlaylistStore() {}
    public static final class Channel {
        public final String name;
        public final String url;
        public final String category;
        public final String logoUrl;
        public Channel(String name,String url,String category,String logoUrl) {
            this.name=name; this.url=url; this.category=category; this.logoUrl=logoUrl;
        }
    }
    public static List<Channel> getChannels(Context context) {
        try(InputStream input=context.getAssets().open("verified_channels.m3u")) {
            return parse(input);
        } catch(IOException e) { return Collections.emptyList(); }
    }
    private static String attr(String src,String key) {
        String open=key+"=\"";
        int p=src.indexOf(open);
        if(p<0)return "";
        p+=open.length();
        int q=src.indexOf('"',p);
        return q<0?"":src.substring(p,q);
    }
    private static List<Channel> parse(InputStream input) throws IOException {
        List<Channel> list=new ArrayList<>();
        String name="",group="",logo="";
        BufferedReader r=new BufferedReader(new InputStreamReader(input,StandardCharsets.UTF_8));
        String line;
        while((line=r.readLine())!=null) {
            line=line.trim();
            if(line.startsWith("#EXTINF:")) {
                int comma=line.lastIndexOf(',');
                name=comma>=0?line.substring(comma+1).trim():"";
                group=attr(line,"group-title");
                logo=attr(line,"tvg-logo");
            } else if(line.startsWith("https://") || line.startsWith("http://")) {
                if(name.length()==0)continue;
                list.add(new Channel(name,line,group,logo));
                name=group=logo="";
            }
        }
        return Collections.unmodifiableList(list);
    }
}
