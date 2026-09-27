import 'package:flutter/material.dart';
import '../data/mock/mock_data.dart';
import '../models/task.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import '../theme/app_spacing.dart';
import '../widgets/advisory_card.dart';
import '../widgets/crop_hero_card.dart';
import '../widgets/health_badge.dart';
import '../widgets/section_title.dart';
import '../widgets/stat_pill.dart';
import '../widgets/task_tile.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late List<FarmTask> _tasks;

  @override
  void initState() {
    super.initState();
    _tasks = List.of(MockData.tasks);
  }

  @override
  Widget build(BuildContext context) {
    final crop = MockData.crops.first;
    final weather = MockData.weather;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpace.xxl),
      child: LayoutBuilder(builder: (context, c) {
        final wide = c.maxWidth > 900;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ---------- Greeting ----------
            Row(children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Good morning, ${MockData.farmerName} 👋',
                        style: AppText.h1),
                    const SizedBox(height: 6),
                    Text("Here's today's farm advisory", style: AppText.bodyMuted),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: AppColors.border),
                ),
                child: Row(children: [
                  const Icon(Icons.wb_sunny_outlined,
                      size: 18, color: AppColors.warning),
                  const SizedBox(width: 8),
                  Text('${weather.tempC}°C · Rain ${weather.rainChance}%',
                      style: AppText.label),
                ]),
              ),
            ]),
            const SizedBox(height: AppSpace.xxl),

            // ---------- Hero ----------
            CropHeroCard(crop: crop),
            const SizedBox(height: AppSpace.xxl),

            // ---------- Quick info ----------
            SectionTitle(title: 'Quick Info'),
            GridView.count(
              crossAxisCount: wide ? 3 : 1,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: AppSpace.lg,
              mainAxisSpacing: AppSpace.lg,
              childAspectRatio: wide ? 2.6 : 3.4,
              children: [
                StatPill(
                  icon: Icons.wb_sunny_outlined,
                  title: 'Weather',
                  value: '${weather.tempC}°C · ${weather.condition}',
                  iconColor: AppColors.warning,
                ),
                StatPill(
                  icon: Icons.water_drop_outlined,
                  title: 'Water',
                  value: 'Medium need',
                  iconColor: AppColors.primary,
                ),
                StatPill(
                  icon: Icons.favorite_border,
                  title: 'Crop Health',
                  value: 'Good · Stable',
                  iconColor: AppColors.good,
                ),
              ],
            ),
            const SizedBox(height: AppSpace.xxl),

            // ---------- Advisory ----------
            SectionTitle(title: "🌱 Today's Advisory"),
            GridView.count(
              crossAxisCount: wide ? 2 : 1,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: AppSpace.lg,
              mainAxisSpacing: AppSpace.lg,
              childAspectRatio: wide ? 2.8 : 2.4,
              children: MockData.advisories
                  .map((a) => AdvisoryCard(advisory: a))
                  .toList(),
            ),
            const SizedBox(height: AppSpace.xxl),

            // ---------- Tasks + Scan CTA ----------
            if (wide)
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Expanded(flex: 3, child: _tasksSection()),
                const SizedBox(width: AppSpace.xl),
                Expanded(flex: 2, child: _scanCTA()),
              ])
            else ...[
              _tasksSection(),
              const SizedBox(height: AppSpace.xl),
              _scanCTA(),
            ],
          ],
        );
      }),
    );
  }

  Widget _tasksSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionTitle(title: "📋 Today's Tasks"),
        Container(
          padding: const EdgeInsets.all(AppSpace.lg),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(AppSpace.radiusCard),
            border: Border.all(color: AppColors.border),
          ),
          child: Column(
            children: List.generate(_tasks.length, (i) {
              return TaskTile(
                task: _tasks[i],
                onChanged: (v) => setState(() => _tasks[i].done = v ?? false),
              );
            }),
          ),
        ),
      ],
    );
  }

  Widget _scanCTA() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionTitle(title: '📷 Daily Crop Check'),
        Container(
          padding: const EdgeInsets.all(AppSpace.xl),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [AppColors.primary, AppColors.accent],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(AppSpace.radiusCard),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.camera_alt_outlined, color: Colors.white, size: 28),
              const SizedBox(height: AppSpace.md),
              Text('Want a more informed advisory?',
                  style: AppText.h3.copyWith(color: Colors.white)),
              const SizedBox(height: 6),
              Text("Upload today's crop photo",
                  style: AppText.body.copyWith(color: Colors.white70)),
              const SizedBox(height: AppSpace.lg),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: () {},
                  icon: const Icon(Icons.camera_alt_outlined, size: 18),
                  label: const Text('Scan Crop'),
                  style: FilledButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: AppColors.primary,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}