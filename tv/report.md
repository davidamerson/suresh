# Sri Lanka TV live-stream verification

Last checked: 2026-11-07 20:28 UTC
**4 out of 13 channels with evidence of playback**

Real decoder rule: FFmpeg must decode five consecutive video frames. The 3 user-confirmed streams are included even if an overseas runner cannot play them.

## Available

- Hiru TV: five decoded video frames on GitHub runner
- Rupavahini: five decoded video frames on GitHub runner
- Siyatha TV: five decoded video frames on GitHub runner
- Shakthi TV: five decoded video frames on GitHub runner

## Not verified
- Sirasa TV
- TV Derana
- Swarnavahini
- ITN
- Supreme TV
- TV1
- Nethra TV
- Vasantham TV
- Ada Derana 24

## Checks and errors
- Hiru TV: PASS; 5 frames; https://tv.hiruhost.com:1936/8012/8012/playlist.m3u8 ; 
- Hiru TV: FAIL; 0 frames; https://tv.lotustechnologieslk.net:1936/8012/8012/playlist.m3u8 ; [tcp @ 0x5638959e8f40] Connection to tcp://tv.lotustechnologieslk.net:1936 failed: Connection timed out | [in#0 @ 0x563895a30340] Error opening input: Connection timed out | Error 
- Rupavahini: PASS; 5 frames; https://rpn.bozztv.com/slrclive/slrc/slrclive/index.m3u8 ; 
- Siyatha TV: PASS; 5 frames; https://rtmp01.voaplus.com/hls/6x6ik312qk4grfxocfcv.m3u8 ; 
- Siyatha TV: FAIL; 0 frames; https://stvlk.live/live/eml079n7ui3ytg1c6x4/index.m3u8 ; [tcp @ 0x55cf4ad575c0] Failed to resolve hostname stvlk.live: Name or service not known | [in#0 @ 0x55cf4ad54340] Error opening input: Input/output error | Error opening input file
- Sirasa TV: FAIL; 0 frames; https://edge2-moblive.yuppcdn.net/transsd/smil:sirtv09.smil/playlist.m3u8?dvr ; [tcp @ 0x559a267aef40] Connection to tcp://edge2-moblive.yuppcdn.net:443 failed: Connection timed out | [in#0 @ 0x559a267f6340] Error opening input: Connection timed out | Error op
- TV Derana: FAIL; 0 frames; https://edge3-moblive.yuppcdn.net/transhd2/smil:detv04.smil/index.m3u8 ; [tcp @ 0x565237a28f40] Connection to tcp://edge3-moblive.yuppcdn.net:443 failed: Connection timed out | [in#0 @ 0x565237a70340] Error opening input: Connection timed out | Error op
- TV Derana: FAIL; 0 frames; https://ythls.armelin.one/channel/UCbkMFGQ_RWIf0OiYeOpf6Ng.m3u8 ; [tcp @ 0x558418457f40] Failed to resolve hostname ythls.armelin.one: No address associated with hostname | [in#0 @ 0x55841849f340] Error opening input: Input/output error | Error o
- Swarnavahini: FAIL; 0 frames; https://teledrama.ebc.lk/TTT/proxy.php ; [in#0 @ 0x56340b357340] Error opening input: Server returned 403 Forbidden (access denied) | Error opening input file https://teledrama.ebc.lk/TTT/proxy.php. | Error opening input 
- Swarnavahini: FAIL; 0 frames; https://jk3lz8xklw79-hls-live.5centscdn.com/efm/098f6bcd4621d373cade4e832627b4f6.sdp/playlist.m3u8 ; [in#0 @ 0x555a7b437340] Error opening input: Server returned 404 Not Found | Error opening input file https://jk3lz8xklw79-hls-live.5centscdn.com/efm/098f6bcd4621d373cade4e832627b4
- ITN: FAIL; 0 frames; https://edge4-moblive.yuppcdn.net/transsd/smil:itn43.smil/playlist.m3u8 ; [tcp @ 0x560e86815f40] Connection to tcp://edge4-moblive.yuppcdn.net:443 failed: Connection timed out | [in#0 @ 0x560e8685d340] Error opening input: Connection timed out | Error op
- ITN: FAIL; 0 frames; https://222103-hls.akamaized.net/668828a00bf80aa436254876/live_aabd3d003af211efadcf7986aa245789/rewind-3600.m3u8 ; [in#0 @ 0x5597de073340] Error opening input: Server returned 403 Forbidden (access denied) | Error opening input file https://222103-hls.akamaized.net/668828a00bf80aa436254876/live
- ITN: FAIL; 0 frames; https://j78dp2pnlq5r-hls-live.comcities.net/ITNDigital/cf467ddf13ba30dd3c71435cafa6fd6e.sdp/playlist_dvr.m3u8 ; [tcp @ 0x556ec6af4740] Failed to resolve hostname j78dp2pnlq5r-hls-live.comcities.net: Name or service not known | [in#0 @ 0x556ec6af1340] Error opening input: Input/output error |
- Shakthi TV: PASS; 5 frames; https://mumbai-edge.smartplaytv.in/ShakthiTV/index.m3u8 ; 
- Shakthi TV: FAIL; 0 frames; https://edge4-moblive.yuppcdn.net/transsd/smil:saktv10.smil/playlist.m3u8?dvr ; [tcp @ 0x56291033ff40] Connection to tcp://edge4-moblive.yuppcdn.net:443 failed: Connection timed out | [in#0 @ 0x562910387340] Error opening input: Connection timed out | Error op
- TV1: FAIL; 0 frames; https://edge4-moblive.yuppcdn.net/trans1sd/smil:tv111.smil/playlist.m3u8 ; [tcp @ 0x55902e634f40] Connection to tcp://edge4-moblive.yuppcdn.net:443 failed: Connection timed out | [in#0 @ 0x55902e67c340] Error opening input: Connection timed out | Error op
- Nethra TV: FAIL; 0 frames; https://edge3-moblive.yuppcdn.net/transsd/smil:chii02.smil/playlist.m3u8?dvr ; [tcp @ 0x556737b88f40] Connection to tcp://edge3-moblive.yuppcdn.net:443 failed: Connection timed out | [in#0 @ 0x556737bd0340] Error opening input: Connection timed out | Error op
- Nethra TV: FAIL; 0 frames; https://ythls.armelin.one/channel/UC6b6XrsNOxQiS-FdfE8-Avw.m3u8 ; [tcp @ 0x55b6a16d9f40] Failed to resolve hostname ythls.armelin.one: No address associated with hostname | [in#0 @ 0x55b6a1721340] Error opening input: Input/output error | Error o
- Vasantham TV: FAIL; 0 frames; https://edge3-moblive.yuppcdn.net/trans1sd/smil:vatv07.smil/playlist.m3u8?dvr ; [tcp @ 0x5622dd55ef40] Connection to tcp://edge3-moblive.yuppcdn.net:443 failed: Connection timed out | [in#0 @ 0x5622dd5a6340] Error opening input: Connection timed out | Error op
- Vasantham TV: FAIL; 0 frames; https://222103-hls.akamaized.net/668828a00bf80aa436254876/live_2cdb4ef03c1311efadcf7986aa245789/rewind-3600.m3u8 ; [in#0 @ 0x5615b130c340] Error opening input: Server returned 403 Forbidden (access denied) | Error opening input file https://222103-hls.akamaized.net/668828a00bf80aa436254876/live
- Hiru TV: FAIL; 0 frames; https://dc2.serverse.com:19360/hirutv/hirutv.m3u8?checkedby:iptvcat.com ; [in#0 @ 0x5608c006b340] Error opening input: Server returned 404 Not Found | Error opening input file https://dc2.serverse.com:19360/hirutv/hirutv.m3u8?checkedby:iptvcat.com. | Err
- Hiru TV: FAIL; 0 frames; https://tv.lotustechnologieslk.net:1936/8012/8012/playlist.m3u8?checkedby:iptvcat.com ; [tcp @ 0x55ba8d8d0f40] Connection to tcp://tv.lotustechnologieslk.net:1936 failed: Connection timed out | [in#0 @ 0x55ba8d918340] Error opening input: Connection timed out | Error 
- Hiru TV: PASS; 5 frames; https://tv.hiruhost.com:1936/8012/8012/playlist.m3u8?checkedby:iptvcat.com ; 
- ITN: FAIL; 0 frames; https://edge4-moblive.yuppcdn.net/transsd/smil:itn43.smil/playlist.m3u8?checkedby:iptvcat.com ; [tcp @ 0x564e178f7f40] Connection to tcp://edge4-moblive.yuppcdn.net:443 failed: Connection timed out | [in#0 @ 0x564e1793f340] Error opening input: Connection timed out | Error op
- ITN: FAIL; 0 frames; https://j78dp2pnlq5r-hls-live.comcities.net/ITNDigital/cf467ddf13ba30dd3c71435cafa6fd6e.sdp/playlist_dvr.m3u8?checkedby:iptvcat.com ; [tcp @ 0x55e787bb85c0] Failed to resolve hostname j78dp2pnlq5r-hls-live.comcities.net: Name or service not known | [in#0 @ 0x55e787bb5340] Error opening input: Input/output error |
- Nethra TV: FAIL; 0 frames; https://ythls.armelin.one/channel/UC6b6XrsNOxQiS-FdfE8-Avw.m3u8?checkedby:iptvcat.com ; [tcp @ 0x564129650f40] Failed to resolve hostname ythls.armelin.one: No address associated with hostname | [in#0 @ 0x564129698340] Error opening input: Input/output error | Error o
- Nethra TV: FAIL; 0 frames; https://edge3-moblive.yuppcdn.net/transsd/smil:chii02.smil/playlist.m3u8?dvr=&checkedby:iptvcat.com ; [tcp @ 0x561fc9542f40] Connection to tcp://edge3-moblive.yuppcdn.net:443 failed: Connection timed out | [in#0 @ 0x561fc958a340] Error opening input: Connection timed out | Error op
- Rupavahini: FAIL; 0 frames; https://edge2-moblive.yuppcdn.net/transsd/smil:runi01.smil/playlist.m3u8?dvr&checkedby:iptvcat.com ; [tcp @ 0x55d6945eaf40] Connection to tcp://edge2-moblive.yuppcdn.net:443 failed: Connection timed out | [in#0 @ 0x55d694632340] Error opening input: Connection timed out | Error op
- Shakthi TV: FAIL; 0 frames; https://edge4-moblive.yuppcdn.net/transsd/smil:saktv10.smil/playlist.m3u8?dvr=&checkedby:iptvcat.com ; [tcp @ 0x562af83a8f40] Connection to tcp://edge4-moblive.yuppcdn.net:443 failed: Connection timed out | [in#0 @ 0x562af83f0340] Error opening input: Connection timed out | Error op
- Sirasa TV: FAIL; 0 frames; https://edge2-moblive.yuppcdn.net/transsd/smil:sirtv09.smil/playlist.m3u8?dvr=&checkedby:iptvcat.com ; [tcp @ 0x556577b20f40] Connection to tcp://edge2-moblive.yuppcdn.net:443 failed: Connection timed out | [in#0 @ 0x556577b68340] Error opening input: Connection timed out | Error op
- Siyatha TV: PASS; 5 frames; https://rtmp01.voaplus.com/hls/6x6ik312qk4grfxocfcv.m3u8?checkedby:iptvcat.com ; 
- Siyatha TV: FAIL; 0 frames; https://stvlk.live/live/eml079n7ui3ytg1c6x4/index.m3u8?checkedby:iptvcat.com ; [tcp @ 0x55c1030b15c0] Failed to resolve hostname stvlk.live: Name or service not known | [in#0 @ 0x55c1030ae340] Error opening input: Input/output error | Error opening input file
- TV1: FAIL; 0 frames; https://edge4-moblive.yuppcdn.net/trans1sd/smil:tv111.smil/playlist.m3u8?checkedby:iptvcat.com ; [tcp @ 0x55cfe615af40] Connection to tcp://edge4-moblive.yuppcdn.net:443 failed: Connection timed out | [in#0 @ 0x55cfe61a2340] Error opening input: Connection timed out | Error op
- TV Derana: FAIL; 0 frames; https://edge3-moblive.yuppcdn.net/transhd2/smil:detv04.smil/index.m3u8?checkedby:iptvcat.com ; [tcp @ 0x559bf6855f40] Connection to tcp://edge3-moblive.yuppcdn.net:443 failed: Connection timed out | [in#0 @ 0x559bf689d340] Error opening input: Connection timed out | Error op
- Vasantham TV: FAIL; 0 frames; https://edge3-moblive.yuppcdn.net/trans1sd/smil:vatv07.smil/playlist.m3u8?dvr=&checkedby:iptvcat.com ; [tcp @ 0x55c89dd9bf40] Connection to tcp://edge3-moblive.yuppcdn.net:443 failed: Connection timed out | [in#0 @ 0x55c89dde3340] Error opening input: Connection timed out | Error op
- Vasantham TV: FAIL; 0 frames; https://j78dp2pnlq5r-hls-live.comcities.net/ITNDigital/20a317b0496a4930b375290505e5d628.sdp/playlist_dvr.m3u8?checkedby:iptvcat.com ; [tcp @ 0x55be689b25c0] Failed to resolve hostname j78dp2pnlq5r-hls-live.comcities.net: Name or service not known | [in#0 @ 0x55be689af340] Error opening input: Input/output error |
- Vasantham TV: FAIL; 0 frames; https://222103-hls.akamaized.net/668828a00bf80aa436254876/live_2cdb4ef03c1311efadcf7986aa245789/rewind-3600.m3u8?checkedby:iptvcat.com ; [in#0 @ 0x556aebb7f340] Error opening input: Server returned 403 Forbidden (access denied) | Error opening input file https://222103-hls.akamaized.net/668828a00bf80aa436254876/live
