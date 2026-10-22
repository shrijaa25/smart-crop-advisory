import 'package:flutter/material.dart';

import '../models/farm.dart';
import '../services/auth_controller.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';
import 'farm_details_screen.dart';
import 'crop_registration_screen.dart';

/// Mandatory setup for farmers without a crop cycle.
/// Guides them through adding a farm when needed, then registering a crop.
class OnboardingWizard extends StatefulWidget {
  final AuthController auth;

  /// Called after the farmer creates a crop cycle and chooses to continue.
  final VoidCallback onFinished;

  const OnboardingWizard({
    super.key,
    required this.auth,
    required this.onFinished,
  });

  @override
  State<OnboardingWizard> createState() => _OnboardingWizardState();
}

class _OnboardingWizardState extends State<OnboardingWizard> {
  int _step = 0; // 0 = welcome, 1 = add farm, 2 = add crop, 3 = done
  List<Farm> _farms = [];
  bool _loading = false;
  String? _farmError;

  @override
  void initState() {
    super.initState();
    _refreshFarms();
  }

  Future<void> _refreshFarms() async {
    setState(() => _loading = true);
    try {
      final farms = await widget.auth.loadFarms();
      if (mounted) {
        setState(() {
          _farms = farms;
          _farmError = null;
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() => _farmError = error.toString());
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _startSetup() {
    if (_farmError != null || _loading) return;
    setState(() => _step = _farms.isEmpty ? 1 : 2);
  }

  Future<void> _goAddFarm() async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => FarmDetailsScreen(auth: widget.auth)),
    );
    if (saved == true && mounted) {
      await _refreshFarms();
      setState(() => _step = 2); // move to add crop
    }
  }

  Future<void> _goAddCrop() async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => CropRegistrationScreen(auth: widget.auth),
      ),
    );
    if (saved == true && mounted) {
      setState(() => _step = 3); // done!
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      child: Scaffold(
        backgroundColor: AppColors.bg,
        appBar: AppBar(
          automaticallyImplyLeading: false,
          title: const Text('Farm setup'),
          actions: [
            TextButton.icon(
              onPressed: widget.auth.logout,
              icon: const Icon(Icons.logout),
              label: const Text('Log out'),
            ),
          ],
        ),
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpace.xxl,
                  vertical: AppSpace.xxl,
                ),
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 350),
                  child: _buildStep(),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStep() {
    switch (_step) {
      case 0:
        return _Welcome(
          key: const ValueKey('welcome'),
          farmerName:
              widget.auth.profile?.fullName.split(' ').first ?? 'Farmer',
          onStart: _startSetup,
          loading: _loading,
          error: _farmError,
          onRetry: _refreshFarms,
        );
      case 1:
        return _StepCard(
          key: const ValueKey('step1'),
          stepNumber: 1,
          totalSteps: 2,
          icon: Icons.add_home_outlined,
          iconColor: AppColors.primary,
          title: 'Add your farm',
          body:
              'Tell us about where you farm — your village, district, land area '
              'and irrigation type. This helps us give you relevant advice.',
          buttonLabel: 'Add Farm',
          onPressed: _goAddFarm,
          loading: _loading,
        );
      case 2:
        return _StepCard(
          key: const ValueKey('step2'),
          stepNumber: 2,
          totalSteps: 2,
          icon: Icons.eco_outlined,
          iconColor: const Color(0xFF2E7D32),
          title: 'Register your crop',
          body:
              'Tell us what you\'ve planted and when. We\'ll use the transplanting '
              'date to track your crop\'s age and automatically create daily tasks.',
          buttonLabel: 'Register Crop',
          onPressed: _goAddCrop,
          loading: _loading,
        );
      case 3:
      default:
        return _Done(key: const ValueKey('done'), onFinish: widget.onFinished);
    }
  }
}

// ──────────────────────────────────────────────────────────────────
// Sub-widgets
// ──────────────────────────────────────────────────────────────────

class _Welcome extends StatelessWidget {
  final String farmerName;
  final VoidCallback onStart;
  final bool loading;
  final String? error;
  final VoidCallback onRetry;

  const _Welcome({
    super.key,
    required this.farmerName,
    required this.onStart,
    required this.loading,
    required this.error,
    required this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            color: AppColors.primaryLight,
            shape: BoxShape.circle,
          ),
          child: const Icon(
            Icons.agriculture_outlined,
            size: 44,
            color: AppColors.primary,
          ),
        ),
        const SizedBox(height: AppSpace.xl),
        Text('Welcome, $farmerName! 👋', style: AppText.h1),
        const SizedBox(height: AppSpace.md),
        Text(
          'Let\'s set up your Smart Crop Advisory in 2 quick steps.\n\n'
          'We\'ll add your farm and register your first crop so the system '
          'can start generating your personalised daily tasks.',
          style: AppText.body,
        ),
        if (error != null) ...[
          const SizedBox(height: AppSpace.lg),
          Text(
            'Unable to load your farms. $error',
            style: AppText.small.copyWith(color: AppColors.danger),
          ),
          TextButton.icon(
            onPressed: loading ? null : onRetry,
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
          ),
        ],
        const SizedBox(height: AppSpace.xxl),
        FilledButton.icon(
          onPressed: loading || error != null ? null : onStart,
          icon: loading
              ? const SizedBox.square(
                  dimension: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.arrow_forward),
          label: Text(loading ? 'Checking your farms…' : 'Get started'),
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
        ),
      ],
    );
  }
}

class _StepCard extends StatelessWidget {
  final int stepNumber;
  final int totalSteps;
  final IconData icon;
  final Color iconColor;
  final String title;
  final String body;
  final String buttonLabel;
  final VoidCallback onPressed;
  final bool loading;

  const _StepCard({
    super.key,
    required this.stepNumber,
    required this.totalSteps,
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.body,
    required this.buttonLabel,
    required this.onPressed,
    required this.loading,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Progress indicator
        Row(
          children: List.generate(totalSteps, (i) {
            final active = i < stepNumber;
            return Expanded(
              child: Container(
                height: 4,
                margin: EdgeInsets.only(right: i < totalSteps - 1 ? 6 : 0),
                decoration: BoxDecoration(
                  color: active ? AppColors.primary : AppColors.border,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            );
          }),
        ),
        const SizedBox(height: AppSpace.xs),
        Text(
          'Step $stepNumber of $totalSteps',
          style: AppText.small,
          textAlign: TextAlign.right,
        ),
        const SizedBox(height: AppSpace.xl),
        Container(
          width: 72,
          height: 72,
          decoration: BoxDecoration(
            color: iconColor.withValues(alpha: 0.12),
            shape: BoxShape.circle,
          ),
          child: Icon(icon, size: 38, color: iconColor),
        ),
        const SizedBox(height: AppSpace.lg),
        Text(title, style: AppText.h2),
        const SizedBox(height: AppSpace.md),
        Text(body, style: AppText.body),
        const SizedBox(height: AppSpace.xxl),
        FilledButton(
          onPressed: loading ? null : onPressed,
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
          child: loading
              ? const SizedBox(
                  width: 22,
                  height: 22,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                )
              : Text(buttonLabel),
        ),
      ],
    );
  }
}

class _Done extends StatelessWidget {
  final VoidCallback onFinish;

  const _Done({super.key, required this.onFinish});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          width: 80,
          height: 80,
          decoration: const BoxDecoration(
            color: Color(0xFFE8F5E9),
            shape: BoxShape.circle,
          ),
          child: const Icon(
            Icons.check_circle_outline,
            size: 48,
            color: AppColors.primary,
          ),
        ),
        const SizedBox(height: AppSpace.xl),
        Text('You\'re all set! 🌱', style: AppText.h1),
        const SizedBox(height: AppSpace.md),
        Text(
          'Your farm and crop are registered. The daily task engine will now '
          'generate personalised guidance every day based on your crop\'s '
          'growth stage and advisory rules.',
          style: AppText.body,
        ),
        const SizedBox(height: AppSpace.xxl),
        FilledButton.icon(
          onPressed: onFinish,
          icon: const Icon(Icons.dashboard_outlined),
          label: const Text('Go to Dashboard'),
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
        ),
      ],
    );
  }
}
