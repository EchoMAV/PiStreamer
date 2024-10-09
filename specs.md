# IMX477 EchoLITE SBX Performance Specs
Below are bench tested results of the IMX477 functioning at various resolutions
and capture modes. Captured video and photo files are saved to the RPi filesystem whilst
the streaming destination a RTP feed to a configuration IP and port.

## Resolution & Aspect Ratio
| Resolution | Aspect Ratio | Notes         |
|------------|--------------|---------------|
| 640x360    | 16:9         | 360p LD       |
| 854x480    | 16:9         | 480p SD       |
| 1280x720   | 16:9         | 720p HD       |
| 1920x1080  | 16:9         | 1080p Full HD |
| 3840x2160  | 16:9         | 4K            |
| 4056x3040  | 4:3          | 12 MP         |

## Streaming Only (2M bitrate)
| Resolution | Avg. Frame Rate | Aspect Ratio | Notes         |
|------------|-----------------|--------------|---------------|
| 640x360    | 50              | 16:9         | 360p LD       |
| 854x480    | 50              | 16:9         | 480p SD       |
| 1280x720   | 45              | 16:9         | 720p HD       |
| 1920x1080  | 20              | 16:9         | 1080p Full HD |

## Streaming + Saved Video (2M bitrate)
| Streaming Resolution | Video Resolution | Avg. Frame Rate |
|----------------------|------------------|-----------------|
| 640x360              | 640x360          | 48              |
| 854x480              | 854x480          | 47              |
| 1280x720             | 1280x720         | 34              |
| 1920x1080            | 1920x1080        | 13              |
| 1280x720             | 3840x2160        | N/A             |

## Streaming + Saved Photo (2M bitrate)
In order to take a photo at higher resolution than streaming resolution, there is a
momentary delay in the camera software to switch between resolutions. Capturing photos
at the same resolution as streaming incurs no significant delay.
| Streaming Resolution | Photo Resolution | Avg. Photo Delay |
|----------------------|------------------|------------------|
| Not 1920x1080        | 1920x1080        | .75 sec          |
| Not 3840x2160        | 3840x2160        | 1.15 sec         |
| Not 4056x3040        | 4056x3040        | 1.42 sec         |


## Streaming + Saved Video + Saved Photo (2M bitrate)
To save a photo at the same resolution as streaming and recording video, there is no
significant impact to fps or streaming delay. However, if capturing a photo at a
higher resolution than streaming+video, the photo delay time above will apply and the
mp4 file up to that point will be saved and a new mp4 file will resume after the photo
has been captured.
