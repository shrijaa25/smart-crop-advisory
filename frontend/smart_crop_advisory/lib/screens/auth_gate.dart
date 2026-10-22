import 'package:flutter/material.dart';

import '../services/auth_controller.dart';
import '../theme/app_colors.dart';
import 'app_shell.dart';
import 'login_screen.dart';
import 'onboarding_wizard.dart';

enum _CropSetupStatus { checking, required, ready, error }

class AuthGate extends StatefulWidget {
  final AuthController auth;
  const AuthGate({super.key, required this.auth});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  _CropSetupStatus _setupStatus = _CropSetupStatus.checking;
  int _checkGeneration = 0;

  @override
  void initState() {
    super.initState();
    widget.auth.addListener(_onAuthChanged);
    if (widget.auth.status == AuthStatus.signedIn) {
      _checkCropCycles();
    }
  }

  @override
  void dispose() {
    widget.auth.removeListener(_onAuthChanged);
    super.dispose();
  }

  void _onAuthChanged() {
    if (widget.auth.status == AuthStatus.signedIn) {
      setState(() => _setupStatus = _CropSetupStatus.checking);
      _checkCropCycles();
    } else {
      // Invalidates an in-flight crop lookup when the farmer logs out/session expires.
      _checkGeneration++;
      setState(() => _setupStatus = _CropSetupStatus.checking);
    }
  }

  Future<void> _checkCropCycles() async {
    final generation = ++_checkGeneration;
    if (mounted) setState(() => _setupStatus = _CropSetupStatus.checking);
    try {
      final cycles = await widget.auth.loadCropCycles();
      if (!mounted ||
          generation != _checkGeneration ||
          widget.auth.status != AuthStatus.signedIn) {
        return;
      }
      setState(
        () => _setupStatus = cycles.isEmpty
            ? _CropSetupStatus.required
            : _CropSetupStatus.ready,
      );
    } catch (_) {
      if (!mounted ||
          generation != _checkGeneration ||
          widget.auth.status != AuthStatus.signedIn) {
        return;
      }
      // Unknown is never treated as an empty list or as dashboard access.
      setState(() => _setupStatus = _CropSetupStatus.error);
    }
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: widget.auth,
    builder: (context, _) {
      switch (widget.auth.status) {
        case AuthStatus.checking:
          return const _SetupLoading(message: 'Checking your session…');
        case AuthStatus.signedOut:
          return LoginScreen(auth: widget.auth);
        case AuthStatus.signedIn:
          return switch (_setupStatus) {
            _CropSetupStatus.checking => const _SetupLoading(
              message: 'Checking your farm setup…',
            ),
            _CropSetupStatus.error => _SetupError(onRetry: _checkCropCycles),
            _CropSetupStatus.required => OnboardingWizard(
              auth: widget.auth,
              onFinished: _checkCropCycles,
            ),
            _CropSetupStatus.ready => AppShell(auth: widget.auth),
          };
      }
    },
  );
}

class _SetupLoading extends StatelessWidget {
  final String message;
  const _SetupLoading({required this.message});
  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: AppColors.bg,
    body: SafeArea(
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 16),
            Text(message),
          ],
        ),
      ),
    ),
  );
}

class _SetupError extends StatelessWidget {
  final VoidCallback onRetry;
  const _SetupError({required this.onRetry});
  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: AppColors.bg,
    body: SafeArea(
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.cloud_off_outlined,
                size: 44,
                color: AppColors.warning,
              ),
              const SizedBox(height: 14),
              Text(
                'Unable to check your crop setup. Please check your connection and try again.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}
