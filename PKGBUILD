# Maintainer: Nirusaki-Malaal
pkgname=nvcontrol
pkgver=3.6.0
pkgrel=1
pkgdesc="Modern GPU switching for NVIDIA Optimus laptops under Linux (Ada Lovelace, Blackwell & Driver 615+ ready)"
arch=('any')
url="https://github.com/Nirusaki-Malaal/NVControl"
license=('MIT')
depends=('python' 'pciutils')
optdepends=('python-pyside6: Modern graphical user interface')
makedepends=('python-build' 'python-installer' 'python-setuptools' 'python-wheel')
provides=('nvcontrol' 'envycontrol')
conflicts=('envycontrol')
source=("$pkgname-$pkgver.tar.gz::$url/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
    cd "$srcdir/$pkgname-$pkgver" 2>/dev/null || cd "$srcdir/$pkgname" 2>/dev/null || cd "$startdir"
    python -m build --wheel --no-isolation
}

package() {
    cd "$srcdir/$pkgname-$pkgver" 2>/dev/null || cd "$srcdir/$pkgname" 2>/dev/null || cd "$startdir"
    python -m installer --destdir="$pkgdir" dist/*.whl
    install -Dm644 nvcontrol.desktop "$pkgdir/usr/share/applications/nvcontrol.desktop"
    install -Dm644 logos/dark.png "$pkgdir/usr/share/icons/hicolor/512x512/apps/nvcontrol.png"
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
