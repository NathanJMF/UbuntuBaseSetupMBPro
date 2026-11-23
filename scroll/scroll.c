#define _GNU_SOURCE
#include <dlfcn.h>
#include <libinput.h>
#include <stdlib.h>
#include <string.h>

static double factor = 1.0;
static double (*native_scroll)(struct libinput_event_pointer *, enum libinput_pointer_axis);

__attribute__((constructor))
static void configure(void)
{
    native_scroll = dlsym(RTLD_NEXT, "libinput_event_pointer_get_scroll_value");
    const char *preload = getenv("LD_PRELOAD");
    Dl_info self;
    if (!preload || !dladdr((void *)configure, &self) || strcmp(preload, self.dli_fname))
        return;
    /* Children launched by Shell must inherit their normal environment. */
    unsetenv("LD_PRELOAD");
    const char *percent = getenv("MACBOOK_FINGER_SCROLL_PERCENT");
    if (percent) {
        char *end;
        long value = strtol(percent, &end, 10);
        if (*percent && !*end && value >= 1 && value <= 200)
            factor = value / 100.0;
        unsetenv("MACBOOK_FINGER_SCROLL_PERCENT");
    }
}

double libinput_event_pointer_get_scroll_value(struct libinput_event_pointer *event,
                                              enum libinput_pointer_axis axis)
{
    if (!native_scroll)
        return 0.0;
    double delta = native_scroll(event, axis);
    struct libinput_event *base = libinput_event_pointer_get_base_event(event);
    if (libinput_event_get_type(base) == LIBINPUT_EVENT_POINTER_SCROLL_FINGER)
        return delta * factor;
    return delta;
}
