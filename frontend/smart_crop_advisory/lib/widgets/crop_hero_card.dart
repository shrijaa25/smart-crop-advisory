import 'package:flutter/material.dart';
import '../models/crop.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import '../theme/app_spacing.dart';
import 'health_badge.dart';

class CropHeroCard extends StatelessWidget {
  final Crop crop;
  final VoidCallback? onView;
  final VoidCallback? onScan;

  const CropHeroCard({super.key, required this.crop, this.onView, this.onScan});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppSpace.radiusCard),
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.surface,
          border: Border.all(color: AppColors.border),
        ),
        child: LayoutBuilder(builder: (context, c) {
          final wide = c.maxWidth > 700;
          final image = ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Image.network(
              crop.imageUrl,
              height: wide ? 260 : 200,
              width: double.infinity,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => Container(
                height: wide ? 260 : 200,
                color: AppColors.primaryLight,
                child: const Center(
                  child: Icon(Icons.image_not_supported_outlined,
                      size: 40, color: AppColors.primary),
                ),
              ),
            ),
          );

          final info = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Row(children: [
                Text(crop.emoji, style: const TextStyle(fontSize: 22)),
                const SizedBox(width: 8),
                Text(crop.name, style: AppText.h2),
              ]),
              const SizedBox(height: AppSpace.sm),
              Text('Day ${crop.dayNumber} • ${crop.stage} Stage',
                  style: AppText.bodyMuted),
              const SizedBox(height: AppSpace.lg),
              Row(children: [
                Text('Crop Health', style: AppText.small),
                const SizedBox(width: 12),
                HealthBadge(level: crop.health, label: crop.healthLabel),
              ]),
              const SizedBox(height: AppSpace.xl),
              Row(children: [
                FilledButton.icon(
                  onPressed: onView,
                  icon: const Icon(Icons.visibility_outlined, size: 18),
                  label: const Text('View Crop'),
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.primaryLight,
                    foregroundColor: AppColors.primary,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 18, vertical: 14),
                  ),
                ),
                const SizedBox(width: AppSpace.md),
                FilledButton.icon(
                  onPressed: onScan,
                  icon: const Icon(Icons.camera_alt_outlined, size: 18),
                  label: const Text('Scan'),
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 18, vertical: 14),
                  ),
                ),
              ]),
            ],
          );

          if (wide) {
            return Padding(
              padding: const EdgeInsets.all(AppSpace.lg),
              child: Row(children: [
                Expanded(flex: 4, child: image),
                const SizedBox(width: AppSpace.xl),
                Expanded(flex: 5, child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpace.sm),
                  child: info,
                )),
              ]),
            );
          }

          return Padding(
            padding: const EdgeInsets.all(AppSpace.lg),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              image,
              const SizedBox(height: AppSpace.lg),
              info,
            ]),
          );
        }),
      ),
    );
  }
}