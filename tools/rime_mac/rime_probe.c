#include "../../assets/rime/rime_api.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <dlfcn.h>
#endif

static double now_ms(void) {
#ifdef _WIN32
  LARGE_INTEGER t, f;
  QueryPerformanceCounter(&t); QueryPerformanceFrequency(&f);
  return (double)t.QuadPart * 1000.0 / (double)f.QuadPart;
#else
  struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
  return t.tv_sec * 1000.0 + t.tv_nsec / 1000000.0;
#endif
}
static int compare_double(const void *a, const void *b) {
  double d = *(const double *)a - *(const double *)b;
  return (d > 0) - (d < 0);
}
int main(int argc, char **argv) {
  if (argc < 4) return 2;
#ifdef _WIN32
  const char *dll = getenv("RIME_TEST_DLL");
  const char *shared = getenv("RIME_TEST_SHARED");
  if (!dll || !shared) return 2;
  HMODULE lib = LoadLibraryA(dll);
  if (!lib) { fprintf(stderr, "LoadLibrary error %lu\n", GetLastError()); return 3; }
  RimeApi *(*get_api)(void) = (RimeApi *(*)(void))GetProcAddress(lib, "rime_get_api");
#else
  void *lib = dlopen("/Library/Input Methods/Squirrel.app/Contents/Frameworks/librime.1.dylib", RTLD_NOW | RTLD_GLOBAL);
  if (!lib) { fprintf(stderr, "%s\n", dlerror()); return 3; }
  if (!dlopen("/Library/Input Methods/Squirrel.app/Contents/Frameworks/rime-plugins/librime-lua.dylib", RTLD_NOW | RTLD_GLOBAL)) {
    fprintf(stderr, "%s\n", dlerror()); return 3;
  }
  RimeApi *(*get_api)(void) = dlsym(lib, "rime_get_api");
#endif
  if (!get_api) return 3;
  RimeApi *api = get_api();
  RIME_STRUCT(RimeTraits, traits);
  const char *modules[] = {"default", "lua", NULL};
#ifdef _WIN32
  traits.shared_data_dir = shared;
#else
  traits.shared_data_dir = "/Library/Input Methods/Squirrel.app/Contents/SharedSupport";
#endif
  traits.user_data_dir = argv[1];
  traits.app_name = "rime.nightingale_probe";
  traits.distribution_name = "Nightingale test";
  traits.distribution_code_name = "nightingale-test";
  traits.modules = modules;
  traits.min_log_level = 1;
  traits.log_dir = argv[1];
  api->setup(&traits);
  api->initialize(&traits);
  fprintf(stderr, "librime %s\n", api->get_version());
  if (!strcmp(argv[3], "--deploy")) {
    api->start_maintenance(True);
    api->join_maintenance_thread();
  }
  RimeSessionId s = api->create_session();
  double schema_begin = now_ms();
  if (!s || !api->select_schema(s, argv[2])) { api->finalize(); return 4; }
  fprintf(stderr, "SCHEMA_INIT_MS %.3f\n", now_ms() - schema_begin);
  api->set_option(s, "ascii_mode", False);
  if (getenv("SHORT_WORDS")) api->set_option(s, "yeying_short_words", True);
  double timings[100000]; size_t n_timings = 0;
  for (int a = 3; a < argc; a++) {
    if (!strcmp(argv[a], "--deploy")) continue;
    if (!strncmp(argv[a], "--switch=", 9)) {
      api->clear_composition(s);
      if (!api->select_schema(s, argv[a] + 9)) { api->finalize(); return 5; }
      api->set_option(s, "ascii_mode", False);
      continue;
    }
    api->clear_composition(s);
    double begin = now_ms();
    if (strspn(argv[a], "abcdefghijklmnopqrstuvwxyz") == strlen(argv[a])) {
      for (const char *p = argv[a]; *p; ++p) {
        double start = now_ms();
        api->process_key(s, *p, 0);
        RIME_STRUCT(RimeContext, intermediate);
        api->get_context(s, &intermediate);
        api->free_context(&intermediate);
        if (n_timings < 100000) timings[n_timings++] = now_ms() - start;
      }
    } else api->simulate_key_sequence(s, argv[a]);
    RIME_STRUCT(RimeContext, ctx);
    api->get_context(s, &ctx);
    printf("%s\t%.3f\t%s", argv[a], now_ms() - begin, api->get_input(s));
    for (int i = 0; i < ctx.menu.num_candidates; i++)
      printf("\t%s", ctx.menu.candidates[i].text);
    printf("\n");
    if (getenv("SHOW_SOURCE")) {
      for (int i = 0; i < ctx.menu.num_candidates; i++)
        printf("SOURCE\t%s\t%d\t%s\n", argv[a], i, ctx.menu.candidates[i].comment ? ctx.menu.candidates[i].comment : "");
    }
    api->free_context(&ctx);
    RIME_STRUCT(RimeCommit, commit);
    if (api->get_commit(s, &commit)) {
      printf("COMMIT\t%s\t%s\n", argv[a], commit.text);
      api->free_commit(&commit);
    }
  }
  if (n_timings) {
    qsort(timings, n_timings, sizeof(double), compare_double);
    printf("METRICS\t%zu\t%.3f\t%.3f\n", n_timings,
      timings[(n_timings - 1) * 95 / 100], timings[n_timings - 1]);
  }
  api->destroy_session(s);
  api->finalize();
  return 0;
}
