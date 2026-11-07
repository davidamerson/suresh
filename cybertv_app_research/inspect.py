import os,re,glob,collections
p='jadx_out/sources/com/cy/cybertv'
patterns={
 'DECRYPT_CIPHER':r'Cipher\.getInstance|SecretKeySpec|IvParameterSpec|AES/|AES\b|decrypt\(',
 'HEX_UTIL':r'hexTo|fromHex|decodeHex|HEX|hexString|decode\(',
 'STREAM_RESOLVE':r'getString\("link"\)|"Vlink"|StreamUrlParser\.parse|StreamAuth|decodeStream|UrlResolver',
 'ENCODING':r'Base64\.decode|android\.util\.Base64|java\.util\.Base64|MessageDigest',
 'DATASOURCE':r'channelss\.db|tvlist|createDataBase|SYNC_URL|RequestTask|JSONObject\(string\)'
}
for label,pattern in patterns.items():
 found=[]
 for f in glob.glob(p+'/**/*.java',recursive=True):
  try:
   t=open(f,'r',encoding='utf8',errors='ignore').read()
  except:continue
  m=re.search(pattern,t,re.I)
  if m:
   found.append((f[len(p)+1:],len(t),m.start()))
 print('CATEGORY',label,'FILES',len(found),flush=True)
 for fn,size,pos in sorted(found,key=lambda v:0 if any(x in v[0] for x in ['StreamUrlParser','Url','Security','Crypto','Decoder','Player','exoActivity','SplashScreen','SyncHelper','StreamAuth']) else 1)[:55]:
  print('FILE',label,fn,'SIZE',size,flush=True)
focus=['StreamUrlParser.java','security/StreamAuth.java','exoActivity.java','SplashScreen.java','ChannelPlayerUtil.java','StreamSelectorHelper.java','SyncHelper.java']
for f in focus:
 fn=os.path.join(p,f)
 if not os.path.isfile(fn):continue
 s=open(fn,encoding='utf8',errors='ignore').read()
 print('FOCUS_FILE',f,'BYTES',len(s))
 pats=[r'Cipher\.getInstance',r'SecretKeySpec',r'getString\("link"\)',r'getString\(5\)',r'getString\(6\)',r'"Vlink"',r'StreamUrlParser\.parse',r'Decrypt',r'decrypt',r'AES',r'new URL\(',r'StreamAuth\.']
 count=0
 for pat in pats:
  for match in list(re.finditer(pat,s,re.I))[:5]:
   a=max(0,match.start()-240);b=min(len(s),match.end()+370);t=s[a:b].replace('\r',' ').replace('\n',' ')
   # show method structure but no literal secrets/tokens/credentials
   t=re.sub(r'(?i)(secret|password|key|token|sig|auth)\s*=\s*"(?:[^"\\]|\\.)*"',r'\1="[REDACTED]"',t)
   t=re.sub(r'https?://[^\s"\\]+','[REMOTE_URL]',t)
   if re.search('getInstance\\([\\x22\\x27]',t):t=re.sub(r'getInstance\\([^)]*\\)','getInstance([TRANSFORMATION])',t)
   print('CONTEXT',f,pat,t[:580],flush=True)
   count+=1
   if count>=40:break
  if count>=40:break
print('COMPLETE')
