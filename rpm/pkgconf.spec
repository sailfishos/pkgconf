# Compatibility macros
%{!?make_build: %global make_build %{__make} %{?_smp_mflags}}
%{!?_rpmmacrodir: %global _rpmmacrodir %{_rpmconfigdir}/macros.d}

%bcond_without pkgconfig_compat
%bcond_with tests


%if %{with pkgconfig_compat}
%global pkgconfig_ver 0.29.2
# For obsoleting pkgconfig, bump the ver to a number higher than latest version
%global pkgconfig_obsver %{pkgconfig_ver}+1
%endif

# pkgconfig platform
# FIXME: %{?_gnu} should be required but our rpm config
# includes the gnu suffixes for some reason
%global pkgconf_target_platform %{_target_platform}

# Search path for pc files for pkgconf
%global pkgconf_libdirs %{_libdir}/pkgconfig:%{_datadir}/pkgconfig

%global somajor 4
%global libname lib%{name}%{somajor}
%global devname lib%{name}-devel

Name:           pkgconf
Version:        2.1.1
Release:        0
Summary:        Package compiler and linker metadata toolkit
License:        ISC
URL:            http://pkgconf.org/
# Mirror at https://releases.pagure.org/pkgconf/pkgconf/
Source0:        https://distfiles.dereferenced.org/%{name}/%{name}-%{version}.tar.xz

# Currently unused
# Simple wrapper scripts to offer platform versions of pkgconfig
Source1:        platform-pkg-config.in

BuildRequires:  gcc
BuildRequires:  make

# For regenerating autotools scripts
BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  libtool

%if %{with tests}
# For unit tests
BuildRequires:  kyua
BuildRequires:  atf-tests
%endif

# pkgconf uses libpkgconf internally
Requires:       %{libname}%{?_isa} = %{version}-%{release}

# This is defined within pkgconf code as a virtual pc (just like in pkgconfig)
Provides:       pkgconfig(pkgconf) = %{version}

%description
pkgconf is a program which helps to configure compiler and linker flags
for development frameworks. It is similar to pkg-config from freedesktop.org
and handles .pc files in a similar manner as pkg-config.

%package -n %{libname}
Summary:        Backend library for %{name}

%description -n %{libname}
This package provides libraries for applications to use the functionality
of %{name}.

%package -n %{devname}
Summary:        Development files for lib%{name}
Requires:       lib%{name}%{?_isa} = %{version}-%{release}

%description -n %{devname}
This package provides files necessary for developing applications
to use functionality provided by %{name}.

%if %{with pkgconfig_compat}
%package m4
Summary:        m4 macros for pkgconf
License:        GPLv2+ with exceptions
BuildArch:      noarch
# Ensure that it Conflicts and Obsoletes pkgconfig since it contains content formerly from it
Conflicts:      pkgconfig < %{pkgconfig_evr}
Obsoletes:      pkgconfig < %{pkgconfig_evr}

%description m4
This package includes m4 macros used to support PKG_CHECK_MODULES
when using pkgconf with autotools.

%package pkg-config
Summary:        %{name} shim to provide /usr/bin/pkg-config
# Ensure that it Conflicts with pkg-config and is considered "better"
License:        ISC
Group:          Development/Tools/Building
Conflicts:      pkg-config < %{pkgconfig_obsver}
Obsoletes:      pkg-config < %{pkgconfig_obsver}
Provides:       pkg-config = %{pkgconfig_obsver}
Provides:       pkg-config%{?_isa} = %{pkgconfig_obsver}
# This is in the original pkgconfig package, set to match output from pkgconf
Provides:       pkgconfig(pkg-config) = %{version}
# Fedora/Mageia pkgconfig Provides for those who might use alternate package name
Provides:       pkgconfig = %{pkgconfig_obsver}
Provides:       pkgconfig%{?_isa} = %{pkgconfig_obsver}
Requires:       %{name}%{?_isa} = %{version}-%{release}
Requires:       %{name}-m4 = %{version}-%{release}

%description pkg-config
This package provides the shim links for pkgconf to be automatically
used in place of pkgconfig. This ensures that pkgconf is used as
the system provider of pkg-config.

%endif


%prep
%autosetup -p1 -n %{name}-%{version}/upstream
autoreconf -fiv

%build

%configure --disable-static \
           --with-pkg-config-dir=%{pkgconf_libdirs} \
           --with-system-includedir=%{_includedir} \
           --with-system-libdir=%{_libdir}

%make_build V=1


%check
%if %{with tests}
make check || :
%endif


%install
%make_install

find %{buildroot} -name '*.la' -print -delete

mkdir -p %{buildroot}%{_sysconfdir}/pkgconfig/personality.d
mkdir -p %{buildroot}%{_datadir}/pkgconfig/personality.d

# pkgconf rpm macros
mkdir -p %{buildroot}%{_rpmmacrodir}/

cat > %{buildroot}%{_rpmmacrodir}/macros.pkgconf <<EOM
%%pkgconfig_personalitydir %{_datadir}/pkgconfig/personality.d
EOM

%if %{with pkgconfig_compat}
install -pm 0755 %{SOURCE1} %{buildroot}%{_bindir}/%{_target_platform}-pkg-config

sed -e "s|@TARGET_PLATFORM@|%{pkgconf_target_platform}|" \
    -e "s|@PKGCONF_LIBDIRS_LOCAL@|/usr/local/%{_lib}/pkgconfig:/usr/local/share/pkgconfig:%{pkgconf_libdirs}|" \
    -e "s|@PKGCONF_SYSLIBDIR_LOCAL@|/usr/local/%{_lib}:%{_libdir}|" \
    -e "s|@PKGCONF_SYSINCDIR_LOCAL@|/usr/local/include:%{_includedir}|" \
    -e "s|@PKGCONF_LIBDIRS@|%{pkgconf_libdirs}|" \
    -e "s|@PKGCONF_SYSLIBDIR@|%{_libdir}|" \
    -e "s|@PKGCONF_SYSINCDIR@|%{_includedir}|" \
    -i %{buildroot}%{_bindir}/%{pkgconf_target_platform}-pkg-config

ln -sr  %{buildroot}%{_bindir}/%{_target_platform}-pkg-config \
   %{buildroot}%{_bindir}/pkg-config

sed -e "s|@PKGCONF_BINDIR@|%{_bindir}|" \
     -i %{buildroot}%{_bindir}/pkg-config
ln -sf pkgconf %{buildroot}%{_bindir}/pkg-config

# Link pkg-config(1) to pkgconf(1)
echo ".so man1/pkgconf.1" > %{buildroot}%{_mandir}/man1/pkg-config.1

mkdir -p %{buildroot}%{_libdir}/pkgconfig
mkdir -p %{buildroot}%{_datadir}/pkgconfig
%endif

# If we're not providing pkgconfig override & compat
# we should not provide the pkgconfig m4 macros
%if ! %{with pkgconfig_compat}
rm -rf %{buildroot}%{_datadir}/aclocal
rm -rf %{buildroot}%{_mandir}/man7
%endif

# Don't install twice
rm -rf %{buildroot}/usr/share/doc/pkgconf/

%post -n %{libname} -p /sbin/ldconfig
%postun -n %{libname} -p /sbin/ldconfig

%files
%license COPYING
%doc README.md AUTHORS NEWS
%{_bindir}/%{name}
%{_bindir}/bomtool
%{_mandir}/man1/%{name}.1*
%{_mandir}/man5/pc.5*
%{_mandir}/man5/%{name}-personality.5*
%{_rpmmacrodir}/macros.pkgconf
%dir %{_sysconfdir}/pkgconfig
%dir %{_sysconfdir}/pkgconfig/personality.d
%dir %{_datadir}/pkgconfig/personality.d

%files -n %{libname}
%license COPYING
%{_libdir}/lib%{name}*.so.%{somajor}
%{_libdir}/lib%{name}*.so.%{somajor}.*

%files -n %{devname}
%{_libdir}/lib%{name}*.so
%{_includedir}/%{name}/
%{_libdir}/pkgconfig/lib%{name}.pc

%if %{with pkgconfig_compat}
%files m4
%{_datadir}/aclocal/pkg.m4
%{_mandir}/man7/pkg.m4.7*

%files pkg-config
%{_bindir}/pkg-config
%{_bindir}/%{_target_platform}-pkg-config
%{_mandir}/man1/pkg-config.1*
%dir %{_libdir}/pkgconfig
%dir %{_datadir}/pkgconfig
%endif
