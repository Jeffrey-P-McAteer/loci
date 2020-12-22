
from build import *

def build(eapp_dir):
  
  # libwidi is responsible for installing USB drivers.
  # it essentially automates what ZaDig does for windows, and we execute
  # this binary as admin before launching the other radio programs.
  #  https://github.com/pbatard/libwdi
  lib_widi_built = (
    os.path.exists(os.path.join(eapp_dir, 'zadic.exe')) or
    not windows_host()
  )

  dump_1090_built = (
    os.path.exists(os.path.join(eapp_dir, 'dump1090.exe')) or
    os.path.exists(os.path.join(eapp_dir, 'dump1090'))
  )

  rtl_ais_built = (
    os.path.exists(os.path.join(eapp_dir, 'rtl_ais.exe')) or
    os.path.exists(os.path.join(eapp_dir, 'rtl_ais'))
  )

  if lib_widi_built and dump_1090_built and rtl_ais_built:
     return

  build_dir = os.path.join(os.path.dirname(eapp_dir), os.path.basename(eapp_dir)+'-misc-build')
  if not os.path.exists(build_dir):
    os.makedirs(build_dir)
  
  libwidi_d = os.path.join(build_dir, 'libwidi')
  rtl_sdr_d = os.path.join(build_dir, 'rtl-sdr')
  dump1090_d = os.path.join(build_dir, 'dump1090')
  rtl_ais_d = os.path.join(build_dir, 'rtl-ais')

  # We need libusb for; most linux systems have it,
  # but because windows does not we clone + build our own copy.
  # this also lets us statically include it in dump1090.exe
  libusb_d = os.path.join(build_dir, 'libusb')
  libusb_static_lib_f = None
  libusb_header_f = None


  # Utility fn used everywhere
  def replace_lines(file, line_begin, line_end, new_content):
    orig_content = ''
    with open(file, 'r') as fd:
      orig_content = fd.read()
      try:
        orig_content = orig_content.decode('utf-8')
      except:
        pass

    orig_lines = [x for x in orig_content.splitlines()]
    new_lines = [x for x in new_content.splitlines()]

    # Handle the dynamic lookup case
    if isinstance(line_begin, str):
      # lookup line where line_begin exists
      for i, l in enumerate(orig_lines):
        if line_begin in l:
          line_begin = i
          line_end = line_begin + line_end
          break

    if isinstance(line_begin, str):
      raise Exception('Cannot find {} in file {}'.format(line_begin, file))

    orig_lines = orig_lines[:line_begin] + new_lines + orig_lines[line_end:]
    new_content = '\n'.join(orig_lines)+'\n'

    with open(file, 'w') as fd:
      fd.write(new_content)




  # download static copies of libusb for use in rtl-sdr and zadic.c

  if windows_host():
    cond_dl_archive_to(
      #'https://github.com/libusb/libusb/releases/download/v1.0.24/libusb-1.0.24.7z',
      'https://repo.msys2.org/mingw/x86_64/mingw-w64-x86_64-libusb-1.0.23-1-any.pkg.tar.xz',
      libusb_d
    )
    #libusb_static_lib_f = os.path.join(libusb_d, 'MinGW64', 'static', 'libusb-1.0.a')
    #libusb_static_lib_f = os.path.join(libusb_d, 'VS2019', 'MS64', 'static', 'libusb-1.0.lib')
    libusb_static_lib_f = os.path.join(libusb_d, 'mingw64', 'lib', 'libusb-1.0.a')

    if not os.path.exists(libusb_static_lib_f):
      raise Exception('Cannot find libusb*.a/.lib at {}'.format(libusb_static_lib_f))

    libusb_header_f = os.path.join(libusb_d, 'mingw64', 'include', 'libusb-1.0', 'libusb.h')
    if not os.path.exists(libusb_header_f):
      raise Exception('Cannot find libusb.h at {}'.format(libusb_header_f))

  else:
    print('WARNING: LibUSB is assumed to exist on linux hosts, skipping download')


  # Build zadic for automatic LibUSB assignment
  # Build libwidi as a static .exe which we can run to install
  # the libusb driver for all devices which look like USB radios.
  if windows_host():
    
    # libwdi is built within the cygwin environment,
    # and that needs libtool. We d/l libtool and add it to the PATH
    # within the cygwin envrionment.

    libtool_bin_d = os.path.join(build_dir, 'libtool')
    cond_dl_archive_to(
      # http://gnuwin32.sourceforge.net/downlinks/libtool-bin-zip.php
      'https://iweb.dl.sourceforge.net/project/gnuwin32/libtool/1.5.28/libtool-1.5.26-bin.zip',
      libtool_bin_d,
    )

    # libtool_bin_d\bin\libtoolize makes an assumption that libtool is un C:\Program Files,
    # but we need it to be libtool_bin_d.
    replace_lines(
      os.path.join(libtool_bin_d, 'bin', 'libtoolize'), 'prefix=', 1,
      'prefix=/cygdrive/c/"{}"'.format(libtool_bin_d.replace('c:', '').replace('C:', '').replace('\\', '/'))
    )

    cond_clone_and_build_repo(
      'https://github.com/pbatard/libwdi.git',
      libwidi_d,
      [
        # C:\msys64\usr\bin\bash -lc "export PATH=/mingw%BITS%/bin:$PATH; cd /c/projects/libwdi; ./bootstrap.sh; ./configure --build=%PLATFORM%-w64-mingw32 --host=%PLATFORM%-w64-mingw32 --enable-toggable-debug --enable-examples-build --disable-debug --disable-shared %EXTRA_OPTS% --with-wdkdir=\"C:/Projects/libwdi/wdk\" --with-wdfver=1011 --with-libusb0=\"C:/Projects/libwdi/libusb-win32-bin-1.2.6.0\" --with-libusbk=\"C:/Projects/libwdi/libusbK-3.0.7.0-bin/bin\"; make -j4"

        [
          'C:\\tools\\cygwin\\bin\\bash.exe',
          '-lc', '''
            cd "{cwd}" ;
            export PATH="C:\\\\tools\\\\cygwin\\\\bin:{libtool_bin_d}\\\\bin:$PATH"  ;
            ./bootstrap.sh ;
            ./configure --enable-static --enable-64bit --enable-examples-build --with-libusb0="{libusb_d}" ;
            make -j4
          '''.format(
            cwd=os.path.abspath(libwidi_d).replace('\\', '\\\\'),
            libusb_d=libusb_d.replace('\\', '\\\\'),
            libtool_bin_d=libtool_bin_d.replace('\\', '\\\\'),
          )
        ]
      ]
    )
    
    libwidi_exe = os.path.join(libwidi_d, 'zadic.exe')
    if not os.path.exists(libwidi_exe):
      raise Exception('Expected a binary to exist at {}'.format(libwidi_exe))
    shutil.copy(libwidi_exe, eapp_dir)




  # Build static RTL-SDR libs for various radio receivers

  def prebuild():
    if libusb_header_f:
      shutil.copy(libusb_header_f, os.path.join(rtl_sdr_d, 'include'))
      os.environ['LIBUSB_INCLUDE_DIRS'] = os.path.join(rtl_sdr_d, 'include')

    if libusb_static_lib_f:
      shutil.copy(libusb_static_lib_f, rtl_sdr_d)
      os.environ['LIBUSB_LIBRARIES'] = rtl_sdr_d

      # For dump1090 build
      shutil.copy(libusb_static_lib_f, os.path.join(rtl_sdr_d, 'src'))
      rtl_lib = os.path.join(rtl_sdr_d, 'lib')
      if not os.path.exists(rtl_lib):
        os.makedirs(rtl_lib)
      shutil.copy(libusb_static_lib_f, rtl_lib)

  def insert_static_libusb_build_steps():
    if libusb_static_lib_f and 'LIBUSB_LIBRARIES' in os.environ:
      
      if shutil.which('pkg-config'):
        # We do not want pkg-cfg to search for a dynamic lib, we build libusb statically on win64
        replace_lines(
          os.path.join(rtl_sdr_d, 'CMakeLists.txt'), 'if(PKG_CONFIG_FOUND)', 7,
          '''
  set(LIBUSB_LIBRARIES "" CACHE STRING "manual libusb path")
  set(LIBUSB_INCLUDE_DIRS "" CACHE STRING "manual libusb includepath")
  set(LIBUSB_FOUND true)
  '''
        )

      contents = ''
      
      with open(os.path.join(rtl_sdr_d, 'src', 'CMakeLists.txt'), 'r') as fd:
        contents = fd.read()

      contents += 'target_link_libraries(rtlsdr "{}") \n'.format(libusb_static_lib_f.replace("\\", "\\\\"))

      with open(os.path.join(rtl_sdr_d, 'src', 'CMakeLists.txt'), 'w') as fd:
        fd.write(contents)


  cond_clone_and_build_repo(
    'https://github.com/osmocom/rtl-sdr.git',
    rtl_sdr_d,
    [
      # Before the build we run prebuild() to copy libusb artifacts
      prebuild,
      insert_static_libusb_build_steps,
      ['cmake', '.'],
      ['make'],
    ]
  )
  # now copy *.a in rtl_sdr_d to rtl_sdr_d/lib
  rtl_lib = os.path.join(rtl_sdr_d, 'lib')
  if not os.path.exists(rtl_lib):
    os.makedirs(rtl_lib)

  lib_files = [
    # Windows artifacts
    os.path.join(rtl_sdr_d, 'src', 'librtlsdr_static.a'),
    os.path.join(rtl_sdr_d, 'src', 'libconvenience_static.a'),
    # linux artifacts
    os.path.join(rtl_sdr_d, 'src', 'librtlsdr.a'),
    os.path.join(rtl_sdr_d, 'src', 'libconvenience_static.a'),
  ]

  for f in lib_files:
    if os.path.exists(f):
      shutil.copy(f, rtl_lib)

  if os.path.exists(os.path.join(rtl_sdr_d, 'src', 'librtlsdr_static.a')):
    shutil.copy(os.path.join(rtl_sdr_d, 'src', 'librtlsdr_static.a'), os.path.join(rtl_lib, 'librtlsdr.a'))

  def patch_dump1090_flightaware():
    if windows_host():
      # The flightaware copy of dump1090 does not compile on windows,
      # so we patch using code from https://github.com/tpainter/dump1090_win

      win_stubs_h = os.path.join(dump1090_d, 'winstubs.h')
      with open(win_stubs_h, 'w') as fd:
        # Content amended from https://github.com/tpainter/dump1090_win/blob/master/winstubs.h
        fd.write('''
#ifndef __WINSTUBS_H
#define __WINSTUBS_H

#include <winsock2.h>
#include <windows.h>
#include <basetsd.h>

typedef UCHAR    uint8_t;
typedef USHORT   uint16_t;
typedef UINT32   uint32_t;
typedef UINT64   uint64_t;
//typedef UINT32   mode_t;
// typedef long     ssize_t;
typedef int      socklen_t;

typedef _Bool bool;

#include <stdatomic.h>

#include <stdio.h>
#include <time.h>
#include <sys/timeb.h>
#include <sys/stat.h>
#include <signal.h>
#include <io.h>
#include <fcntl.h>

#define M_PI 3.14159265358979323846
#include <math.h>
#include <pthread.h>
// #include <winposixclock.h>
// #include <endian.h>

#ifdef __cplusplus
extern "C" {
#endif

//Remove gcc specific __atribute__
#define __attribute__(A)

//Functions not included in the MSVC maths library. This will do for our use.
// _inline double round(double d) {return floor(d + 0.5);}
// _inline double trunc(double d) {return (d>0) ? floor(d):ceil(d) ;}

//usleep works in microseconds, and isn't supported in Windows. This will do for our use.
// _inline void usleep(UINT32 ulSleep) {Sleep(ulSleep/1000);} 
// _inline uint64_t strtoll(const char *p, void *e, UINT32 base) {return _atoi64(p);}
_inline int inet_aton(const char * cp, DWORD * ulAddr) { *ulAddr = inet_addr(cp); return (INADDR_NONE != *ulAddr);} 
#define snprintf  _snprintf
#define vsnprintf _vsnprintf
#define strcasecmp _stricmp
#define realpath(N,R) _fullpath((R),(N),_MAX_PATH)

//enum {
//  PATH_MAX = MAX_PATH
//};

//Windows doesn't have localtime_r
_inline struct tm *localtime_r(time_t *_clock, struct tm *_result)
{
    _localtime64_s(_result, _clock);
    return _result;
}

_inline void cls() {
    HANDLE hStdOut = GetStdHandle(STD_OUTPUT_HANDLE);
    COORD coord = {0, 0};
    DWORD count;

    CONSOLE_SCREEN_BUFFER_INFO csbi;
    GetConsoleScreenBufferInfo(hStdOut, &csbi);

    FillConsoleOutputCharacter(hStdOut, ' ', csbi.dwSize.X * csbi.dwSize.Y, coord, &count);

    SetConsoleCursorPosition(hStdOut, coord);
}

/* FILETIME of Jan 1 1970 00:00:00. */
//static const unsigned __int64 epoch = ((unsigned __int64) 116444736000000000ULL);

/*
 * timezone information is stored outside the kernel so tzp isn't used anymore.
 *
 * Note: this function is not for Win32 high precision timing purpose. See
 * elapsed_time().
 */
/*_inline int gettimeofday(struct timeval * tp, struct timezone * tzp)
{
    (void)(tzp); // make gcc compiler warning go away
    FILETIME    file_time;
    SYSTEMTIME  system_time;
    ULARGE_INTEGER ularge;

    GetSystemTime(&system_time);
    SystemTimeToFileTime(&system_time, &file_time);
    ularge.LowPart = file_time.dwLowDateTime;
    ularge.HighPart = file_time.dwHighDateTime;

    //tp->tv_sec = (long) ((ularge.QuadPart - epoch) / 10000000L);
    tp->tv_sec = (long) ((ularge.QuadPart - ((unsigned __int64) 116444736000000000ULL)) / 10000000L);
    tp->tv_usec = (long) (system_time.wMilliseconds * 1000);

    return 0;
}*/


#define STDIN_FILENO 0
//#define EINPROGRESS  WSAEINPROGRESS
//#define EWOULDBLOCK  WSAEWOULDBLOCK

#ifdef __cplusplus
}
#endif

#endif // __WINSTUBS_H

// Also chuck this in for le16toh : https://gist.github.com/panzi/6856583

#ifndef PORTABLE_ENDIAN_H__
#define PORTABLE_ENDIAN_H__

#if (defined(_WIN16) || defined(_WIN32) || defined(_WIN64)) && !defined(__WINDOWS__)

# define __WINDOWS__

#endif

#if defined(__linux__) || defined(__CYGWIN__)

# include <endian.h>

#elif defined(__APPLE__)

# include <libkern/OSByteOrder.h>

# define htobe16(x) OSSwapHostToBigInt16(x)
# define htole16(x) OSSwapHostToLittleInt16(x)
# define be16toh(x) OSSwapBigToHostInt16(x)
# define le16toh(x) OSSwapLittleToHostInt16(x)
 
# define htobe32(x) OSSwapHostToBigInt32(x)
# define htole32(x) OSSwapHostToLittleInt32(x)
# define be32toh(x) OSSwapBigToHostInt32(x)
# define le32toh(x) OSSwapLittleToHostInt32(x)
 
# define htobe64(x) OSSwapHostToBigInt64(x)
# define htole64(x) OSSwapHostToLittleInt64(x)
# define be64toh(x) OSSwapBigToHostInt64(x)
# define le64toh(x) OSSwapLittleToHostInt64(x)

# define __BYTE_ORDER    BYTE_ORDER
# define __BIG_ENDIAN    BIG_ENDIAN
# define __LITTLE_ENDIAN LITTLE_ENDIAN
# define __PDP_ENDIAN    PDP_ENDIAN

#elif defined(__OpenBSD__)

# include <sys/endian.h>

#elif defined(__NetBSD__) || defined(__FreeBSD__) || defined(__DragonFly__)

# include <sys/endian.h>

# define be16toh(x) betoh16(x)
# define le16toh(x) letoh16(x)

# define be32toh(x) betoh32(x)
# define le32toh(x) letoh32(x)

# define be64toh(x) betoh64(x)
# define le64toh(x) letoh64(x)

#elif defined(__WINDOWS__)

# include <winsock2.h>
# include <sys/param.h>

# if BYTE_ORDER == LITTLE_ENDIAN

#   define htobe16(x) htons(x)
#   define htole16(x) (x)
#   define be16toh(x) ntohs(x)
#   define le16toh(x) (x)
 
#   define htobe32(x) htonl(x)
#   define htole32(x) (x)
#   define be32toh(x) ntohl(x)
#   define le32toh(x) (x)
 
#   define htobe64(x) htonll(x)
#   define htole64(x) (x)
#   define be64toh(x) ntohll(x)
#   define le64toh(x) (x)

# elif BYTE_ORDER == BIG_ENDIAN

    /* that would be xbox 360 */
#   define htobe16(x) (x)
#   define htole16(x) __builtin_bswap16(x)
#   define be16toh(x) (x)
#   define le16toh(x) __builtin_bswap16(x)
 
#   define htobe32(x) (x)
#   define htole32(x) __builtin_bswap32(x)
#   define be32toh(x) (x)
#   define le32toh(x) __builtin_bswap32(x)
 
#   define htobe64(x) (x)
#   define htole64(x) __builtin_bswap64(x)
#   define be64toh(x) (x)
#   define le64toh(x) __builtin_bswap64(x)

# else

#   error byte order not supported

# endif

# define __BYTE_ORDER    BYTE_ORDER
# define __BIG_ENDIAN    BIG_ENDIAN
# define __LITTLE_ENDIAN LITTLE_ENDIAN
# define __PDP_ENDIAN    PDP_ENDIAN

#else

# error platform not supported

#endif

#endif


''')

      inserted_header = '''
#ifndef _WIN32
    #include <stdio.h>
    #include <string.h>
    #include <stdlib.h>
    #include <stdbool.h>
    #include <stdatomic.h>
    #include <pthread.h>
    #include <stdint.h>
    #include <errno.h>
    #include <unistd.h>
    #include <math.h>
    #include <sys/time.h>
    #include <signal.h>
    #include <fcntl.h>
    #include <ctype.h>
    #include <sys/stat.h>
    #include <sys/ioctl.h>
    #include <time.h>
    #include <limits.h>
#else
    #include "winstubs.h" //Put everything Windows specific in here
#endif
      '''

      # For each header file we swap out a group of linux #include statements
      # and put in inserted_header.
      header_files_and_line_nums = [
        (os.path.join(dump1090_d, 'dump1090.h'), 62, 85),
        #(os.path.join(dump1090_d, 'anet.c'), 53, 68),
      ]

      for h_f, line_a, line_b in header_files_and_line_nums:
        h_content = ''
        with open(h_f, 'r') as fd:
          h_content = fd.read()
          try:
            h_content = h_content.decode('utf-8')
          except:
            pass

        # Replace lines line_a-line_b with these lines:
        h_lines = [x for x in h_content.splitlines()]
        inserted_lines = [x for x in inserted_header.splitlines()]
        h_lines = h_lines[:line_a] + inserted_lines + h_lines[line_b:]

        with open(h_f, 'w') as fd:
          fd.write('\n'.join(h_lines)+'\n')

      # now make small, single-line changes

      replace_lines(
        os.path.join(dump1090_d, 'anet.c'), 53, 68,
        '''
#ifndef _WIN32
  #include <sys/types.h>
  #include <sys/socket.h>
  #include <sys/stat.h>
  #include <sys/un.h>
  #include <netinet/in.h>
  #include <netinet/tcp.h>
  #include <arpa/inet.h>
  #include <unistd.h>
  #include <fcntl.h>
  #include <string.h>
  #include <netdb.h>
  #include <errno.h>
  #include <stdarg.h>
  #include <stdio.h>
#else
  #include "winstubs.h" //Put everything Windows specific in here
  #include "dump1090.h"
#endif

        '''
      )

      replace_lines(
        os.path.join(dump1090_d, 'anet.c'), 'int anetNonBlock(char *err, int fd)', 19,
        '''int anetNonBlock(char *err, int fd)
{
    int flags;
#ifndef _WIN32
    /* Set the socket nonblocking.
     * Note that fcntl(2) for F_GETFL and F_SETFL can't be
     * interrupted by a signal. */
    if ((flags = fcntl(fd, F_GETFL)) == -1) {
        anetSetError(err, "fcntl(F_GETFL): %s", strerror(errno));
        return ANET_ERR;
    }
    if (fcntl(fd, F_SETFL, flags | O_NONBLOCK) == -1) {
        anetSetError(err, "fcntl(F_SETFL,O_NONBLOCK): %s", strerror(errno));
        return ANET_ERR;
    }
#else
    flags = 1;
    if (ioctlsocket(fd, FIONBIO, &flags)) {
        errno = WSAGetLastError();
        anetSetError(err, "ioctlsocket(FIONBIO): %s", strerror(errno));
        return ANET_ERR;
    }
#endif
    return ANET_OK;
}
        '''
      )

      replace_lines(
        os.path.join(dump1090_d, 'anet.c'), 'static int anetTcpGenericConnect(char *err', 48,
        '''static int anetTcpGenericConnect(char *err, char *addr, int port, int flags)
{
    int s;
    struct sockaddr_in sa;

    if ((s = anetCreateSocket(err,AF_INET)) == ANET_ERR)
        return ANET_ERR;

    memset(&sa,0,sizeof(sa));
    sa.sin_family = AF_INET;
    sa.sin_port = htons((uint16_t)port);
    if (inet_aton(addr, (void*)&sa.sin_addr) == 0) {
        struct hostent *he;

        he = gethostbyname(addr);
        if (he == NULL) {
            anetSetError(err, "can't resolve: %s", addr);
#ifdef _WIN32
      closesocket(s);
#else
      close(s);
#endif
            return ANET_ERR;
        }
        memcpy(&sa.sin_addr, he->h_addr, sizeof(struct in_addr));
    }
    if (flags & ANET_CONNECT_NONBLOCK) {
        if (anetNonBlock(err,s) != ANET_OK)
            return ANET_ERR;
    }
    if (connect(s, (struct sockaddr*)&sa, sizeof(sa)) == -1) {
        if (errno == EINPROGRESS &&
            flags & ANET_CONNECT_NONBLOCK)
            return s;

        anetSetError(err, "connect: %s", strerror(errno));
#ifdef _WIN32
    closesocket(s);
#else
    close(s);
#endif
        return ANET_ERR;
    }
    return s;
}
        '''
      )

      replace_lines(
        os.path.join(dump1090_d, 'anet.c'), 'static int anetCreateSocket(char *err', 17,
        '''static int anetCreateSocket(char *err, int domain) {
    int s, on = 1;
    if ((s = socket(domain, SOCK_STREAM, 0)) == -1) {
#ifdef _WIN32
        errno = WSAGetLastError();
#endif
        anetSetError(err, "creating socket: %d %s", errno, strerror(errno));
        return ANET_ERR;
    }

    /* Make sure connection-intensive things like the redis benckmark
     * will be able to close/open sockets a zillion of times */
    if (setsockopt(s, SOL_SOCKET, SO_REUSEADDR, (void*)&on, sizeof(on)) == -1) {
        anetSetError(err, "setsockopt SO_REUSEADDR: %s", strerror(errno));
        return ANET_ERR;
    }
    return s;
}
        '''
      )

      replace_lines(
        os.path.join(dump1090_d, 'anet.h'), 'int anetTcpConnect(char *err', 1,
        'int anetTcpConnect(char *err, char *addr, int port);'
      )

      replace_lines(
        os.path.join(dump1090_d, 'anet.c'), 'int anetTcpConnect(char *err', 5,
        '''int anetTcpConnect(char *err, char *addr, int port)
{
    return anetTcpGenericConnect(err,addr,port,ANET_CONNECT_NONE);
}
        '''
      )

      replace_lines(
        os.path.join(dump1090_d, 'anet.h'), 'int anetTcpNonBlockConnect(char *err', 1,
        'int anetTcpNonBlockConnect(char *err, char *addr, int port);'
      )

      replace_lines(
        os.path.join(dump1090_d, 'anet.c'), 'int anetTcpNonBlockConnect(char *err', 5,
        '''int anetTcpNonBlockConnect(char *err, char *addr, int port)
{
    return anetTcpGenericConnect(err,addr,port,ANET_CONNECT_NONBLOCK);
}
        '''
      )

      replace_lines(
        os.path.join(dump1090_d, 'anet.c'), 'static int anetListen(char *err, int s', 23,
        '''static int anetListen(char *err, int s, struct sockaddr *sa, socklen_t len) {
    if (bind(s,sa,len) == -1) {
#ifdef _WIN32
        errno = WSAGetLastError();
#endif
        anetSetError(err, "bind: %s", strerror(errno));
#ifdef _WIN32
    closesocket(s);
#else
    close(s);
#endif
        return ANET_ERR;
    }

    /* Use a backlog of 512 entries. We pass 511 to the listen() call because
     * the kernel does: backlogsize = roundup_pow_of_two(backlogsize + 1);
     * which will thus give us a backlog of 512 entries */
    if (listen(s, 511) == -1) {
#ifdef _WIN32
        errno = WSAGetLastError();
#endif
        anetSetError(err, "listen: %s", strerror(errno));
#ifdef _WIN32
    closesocket(s);
#else
    close(s);
#endif
        return ANET_ERR;
    }
    return ANET_OK;
}
        '''
      )

      replace_lines(
        os.path.join(dump1090_d, 'anet.h'), 'int anetTcpServer(char *err,', 1,
        'int anetTcpServer(char *err, int port, char *bindaddr, int *fds, int nfds);'
      )

      replace_lines(
        os.path.join(dump1090_d, 'anet.c'), 'int anetTcpServer(char *err,', 38,
        '''int anetTcpServer(char *err, int port, char *bindaddr, int *fds, int nfds)
{
    int s;
    struct sockaddr_in sa;

    if ((s = anetCreateSocket(err,AF_INET)) == ANET_ERR)
        return ANET_ERR;

    memset(&sa,0,sizeof(sa));
    sa.sin_family = AF_INET;
    sa.sin_port = htons((uint16_t)port);
    sa.sin_addr.s_addr = htonl(INADDR_ANY);
    if (bindaddr && inet_aton(bindaddr, (void*)&sa.sin_addr) == 0) {
        anetSetError(err, "invalid bind address");
#ifdef _WIN32
    closesocket(s);
#else
    close(s);
#endif
        return ANET_ERR;
    }
    if (anetListen(err,s,(struct sockaddr*)&sa,sizeof(sa)) == ANET_ERR)
        return ANET_ERR;
    return s;
}
        '''
      )



      replace_lines(
        os.path.join(dump1090_d, 'interactive.c'), 78, 227,
        '''void interactiveShowData(void) {
    struct aircraft *a = Modes.aircrafts;
    static uint64_t next_update;
    uint64_t now = mstime();
    int count = 0;
    char progress;
    char spinner[4] = "|/-\\\\";

    if (!Modes.interactive)
        return;

    // Refresh screen every (MODES_INTERACTIVE_REFRESH_TIME) miliseconde
    if (now < next_update)
        return;

    next_update = now + MODES_INTERACTIVE_REFRESH_TIME;

    progress = spinner[(now/1000)%4];

#ifndef _WIN32
    printf("\\x1b[H\\x1b[2J");    // Clear the screen
#else
    cls();
#endif

    if (Modes.interactive == 0) {
        printf (
" Hex    Mode  Sqwk  Flight   Alt    Spd  Hdg    Lat      Long   RSSI  Msgs  Ti%c\\n", progress);
    } else {
        printf (
" Hex   Flight   Alt      V/S GS  TT  SSR  G*456^ Msgs    Seen %c\\n", progress);
    }
    printf(
"-------------------------------------------------------------------------------\\n");

    while(a && (count < 16)) { // Used to have a dynamic # of interactive rows

        if (a->reliable && (now - a->seen) < Modes.interactive_display_ttl) {
            int msgs  = a->messages;
            
            char strSquawk[5] = " ";
            char strFl[7]     = " ";
            char strTt[5]     = " ";
            char strGs[5]     = " ";
            
            char strMode[5]               = "    ";
            char strLat[8]                = " ";
            char strLon[9]                = " ";
            
            double* pSig                 = a->signalLevel;
            
            double signalAverage = (pSig[0] + pSig[1] + pSig[2] + pSig[3] + 
                                    pSig[4] + pSig[5] + pSig[6] + pSig[7]) / 8.0; 

            if (trackDataValid(&a->squawk_valid)) {
                snprintf(strSquawk,5,"%04x", a->squawk);
            }

            if (trackDataValid(&a->gs_valid)) {
                snprintf (strGs, 5,"%3d", convert_speed(a->gs));
            }

            if (trackDataValid(&a->track_valid)) {
                snprintf (strTt, 5,"%03.0f", a->track);
            }

            strMode[0] = 'S';
            if (a->adsb_version >= 0) {
                strMode[1] = '0' + a->adsb_version;
            }
            if (a->modeA_hit) {
                strMode[2] = 'a';
            }
            if (a->modeC_hit) {
                strMode[3] = 'c';
            }

            if (trackDataValid(&a->position_valid)) {
                snprintf(strLat, 8,"%7.03f", a->lat);
                snprintf(strLon, 9,"%8.03f", a->lon);
            }

            if (trackDataValid(&a->airground_valid) && a->airground == AG_GROUND) {
                snprintf(strFl, 7," grnd");
            } else if (Modes.use_gnss && trackDataValid(&a->altitude_geom_valid)) {
                snprintf(strFl, 7, "%5dH", convert_altitude(a->altitude_geom));
            } else if (trackDataValid(&a->altitude_baro_valid)) {
                snprintf(strFl, 7, "%5d ", convert_altitude(a->altitude_baro));
            }

            printf("%s%06X %-4s  %-4s  %-8s %5s  %3s  %3s  %7s %8s %5.1f %5d %2.0f\\n",
                   (a->addr & MODES_NON_ICAO_ADDRESS) ? "~" : " ", (a->addr & 0xffffff),
                   strMode, strSquawk, a->callsign, strFl, strGs, strTt,
                   strLat, strLon, 10 * log10(signalAverage), msgs, (now - a->seen)/1000.0);
            
            count++;
        }
        a = a->next;
    }
}

void interactiveInit(void) {
  // unused
}

void interactiveCleanup(void) {
  // unused
}

void interactiveNoConnection(void) {
  printf("interactiveNoConnection not implemented!\\n");
}

        '''
      )
      replace_lines(
        os.path.join(dump1090_d, 'interactive.c'), 51, 53,
        '' # removes "#include <curses.h>"
      )


      replace_lines(
        os.path.join(dump1090_d, 'net_io.c'), 'struct client *serviceConnect(struct net_service', 13,
        '''struct client *serviceConnect(struct net_service *service, char *addr, int port)
{
    int s;
    s = anetTcpConnect(Modes.aneterr, addr, port);
    if (s == ANET_ERR)
        return NULL;
    return createSocketClient(service, s);
}
        '''
      )

      replace_lines(
        os.path.join(dump1090_d, 'net_io.c'), 'nfds = anetTcpServer(Modes.aneterr, buf, bind_addr, newfds, sizeof(newfds));', 1,
        '''
int port = atoi(buf);
nfds = anetTcpServer(Modes.aneterr, port, bind_addr, newfds, sizeof(newfds));
        '''
      )

      replace_lines(
        os.path.join(dump1090_d, 'net_io.c'), 'signal(SIGPIPE, SIG_IGN);', 1,
        '// signal(SIGPIPE, SIG_IGN);'
      )

      replace_lines(
        os.path.join(dump1090_d, 'net_io.c'), 'gmtime_r(&received, &stTime_receive);', 1,
        'gmtime_s(&received, &stTime_receive);'
      )

      replace_lines(
        os.path.join(dump1090_d, 'demod_2400.c'), '#include <gd.h>', 2, # 2 removes the #endif as well
        '// #include <gd.h>'
      )

      replace_lines(
        os.path.join(dump1090_d, 'demod_2400.c'), 23, 24,
        '#define M_SQRT2 1.41421356237309504880'
      )

      replace_lines(
        os.path.join(dump1090_d, 'stats.c'), 'void display_stats(struct stats', 118,
        '''void display_stats(struct stats *st) {
        printf("\\n\\nNo stats, sorry. Windows does not understand some formatters we need.\\n\\n");
}
        '''
      )

      replace_lines(
        os.path.join(dump1090_d, 'view1090.c'), 'if (!Modes.quiet) {showCopyright', 1,
        '// if (!Modes.quiet) {showCopyright();} '
      )

      replace_lines(
        os.path.join(dump1090_d, 'view1090.c'), 'sleep(1);', 1,
        'Sleep(1);'
      )

      replace_lines(
        os.path.join(dump1090_d, 'view1090.c'), 'if ( (!Modes.wsaData.wVersion', 2,
        '{ printf("Calling WSAStartup....\\n"); '
      )

      replace_lines(
        os.path.join(dump1090_d, 'net_io.c'), 'void modesInitNet(void) {', 1,
        '''void modesInitNet(void) {
#ifdef _WIN32
        if (WSAStartup(MAKEWORD(2,1),&Modes.wsaData) != 0)
        {
          fprintf(stderr, "WSAStartup returned Error\\n");
        }
#endif
'''
      )


      replace_lines(
        os.path.join(dump1090_d, 'Makefile'), 'CFLAGS += $(DIALECT)', 1,
        # let warnings be warnings (removed -Werror)
        'CFLAGS += $(DIALECT) -O3 -g -DENABLE_RTLSDR -Wall -Wmissing-declarations -W -D_DEFAULT_SOURCE -fno-common -Wno-missing-declarations '+
          '-Wno-unused-but-set-variable -Wno-unused-variable -Wno-unused-function -Wno-incompatible-pointer-types '+
          '-Wno-unused-parameter '
      )

      replace_lines(
        os.path.join(dump1090_d, 'Makefile'), '$(CC) -g -o $@ $^ $(LDFLAGS) $(LIBS) $(LIBS_SDR) -lncurses', 1,
        '\t$(CC) -g -o $@ $^ -DENABLE_RTLSDR -L"{}" -Wl,-Bstatic -lrtlsdr_static -lusb-1.0 -Wl,-Bdynamic $(LDFLAGS) -Wl,--allow-multiple-definition -lWs2_32 $(LIBS) $(LIBS_SDR)'.format(rtl_lib)
      )

      replace_lines(
        os.path.join(dump1090_d, 'Makefile'), '$(CC) -g -o $@ $^ $(LDFLAGS) $(LIBS) -lncurses', 1,
        '\t$(CC) -g -o $@ $^ -DENABLE_RTLSDR -L"{}" -Wl,-Bstatic -lrtlsdr_static -lusb-1.0 -Wl,-Bdynamic $(LDFLAGS) -Wl,--allow-multiple-definition -lWs2_32 $(LIBS)'.format(rtl_lib)
      )

      # Modify environ for make command, part of bash/mingw double-escapes the windows pathsep.
      os.environ['CC'] = os.path.basename(shutil.which('gcc'))
      

  cond_clone_and_build_repo(
    'https://github.com/flightaware/dump1090.git',
    dump1090_d,
    [
      patch_dump1090_flightaware,
      ['make', 'RTLSDR_PREFIX={}'.format(rtl_sdr_d), 'STATIC=yes', 'RTLSDR=yes'],
    ]
  )

  # Finally copy out the ./dump1090[.exe] artifact which does not depend on libsdr
  exe_name = 'dump1090.exe'
  dump1090_exe = os.path.join(dump1090_d, exe_name)
  if not os.path.exists(dump1090_exe):
    exe_name = 'dump1090'
    dump1090_exe = os.path.join(dump1090_d, exe_name)

  shutil.copy(dump1090_exe, eapp_dir)


  # Now build the rtl-ais program to receive ais data.
  # Same strategy, we use the static copy of rtl-sdr
  # to make the .exe file not depend on anything except hardware.

  def patch_rtl_ais_for_static_compile():
    replace_lines(
      os.path.join(rtl_ais_d, 'Makefile'), 0, 41,
      '''CFLAGS?=-O2 -g -Wall -W 
CFLAGS+= -I./aisdecoder -I./aisdecoder/lib -I./tcp_listener -I"{rtl_include}"
LDFLAGS+=-lpthread -lm -L"{rtl_lib}" -L"{libusb_apparently}" -Wl,-Bstatic -lrtlsdr -Wl,-Bdynamic {libusb_flags}

      '''.format(
        rtl_include=os.path.join(rtl_sdr_d, 'include'),
        rtl_lib=os.path.join(rtl_sdr_d, 'lib'),
        libusb_apparently=rtl_sdr_d,
        libusb_flags='-Wl,-Bstatic -lusb-1.0 -Wl,-Bdynamic -lWs2_32'.format(rtl_sdr_d) if windows_host() else '-lusb-1.0',

      )
    )

  cond_clone_and_build_repo(
    'https://github.com/dgiardini/rtl-ais.git',
    rtl_ais_d,
    [
      patch_rtl_ais_for_static_compile,
      ['make'],
    ]
  )

  exe_name = 'rtl_ais.exe'
  rtl_ais_exe = os.path.join(rtl_ais_d, exe_name)
  if not os.path.exists(rtl_ais_exe):
    exe_name = 'rtl_ais'
    rtl_ais_exe = os.path.join(rtl_ais_d, exe_name)

  shutil.copy(rtl_ais_exe, eapp_dir)


  return os.path.join(eapp_dir, exe_name)

