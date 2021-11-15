class KonamiCodeHandler {
    constructor (cssSelector, display) {
        this.cssSelector = cssSelector;
        this.display = display;
        this.current = 0;
        this.code = [
            'ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight',
            'ArrowLeft', 'ArrowRight', 'b', 'a'
        ];
    }

    keyHandler (e) {
        // If the key isn't in the pattern or isn't the current key in the pattern, reset
        if (this.code.indexOf(e.key) < 0 || e.key !== this.code[this.current]) {
            this.current = 0;
            return;
        }

        // Update how much of the pattern is complete
        this.current++;

        // If complete, alert and reset
        if (this.code.length === this.current) {
            this.current = 0;
            document.querySelectorAll(this.cssSelector)[0].style.display = this.display;
            window.alert('Are you a wizard?');
        }
    }
}


async function main() {
    var konami = new KonamiCodeHandler('.md-tabs__item:last-child', 'inline-block');
    document.addEventListener('keydown', function (e) { konami.keyHandler(e); }, false);
}


main()
