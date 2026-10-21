export type FeatureItem = {
  title: string;
  description: string;
};

type FeaturesProps = {
  sectionId?: string;
  headingId: string;
  title: string;
  description: string;
  items: FeatureItem[];
  backgroundClassName?: string;
  borderedCards?: boolean;
};

type FeatureCardProps = FeatureItem & {
  bordered?: boolean;
};

function FeatureCard({ title, description, bordered = false }: FeatureCardProps) {
  return (
    <article
      className={[
        "rounded-xl p-6",
        bordered
          ? "border border-gray-200 bg-white transition hover:shadow-md dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700"
          : "bg-white/60 dark:bg-slate-900/60",
      ].join(" ")}
    >
      <h3 className="mb-2 text-xl font-semibold text-gray-900 dark:text-white">{title}</h3>
      <p className="text-gray-600 dark:text-slate-300">{description}</p>
    </article>
  );
}

export function Features({
  sectionId,
  headingId,
  title,
  description,
  items,
  backgroundClassName = "bg-white dark:bg-slate-900",
  borderedCards = false,
}: FeaturesProps) {
  return (
    <section
      id={sectionId}
      aria-labelledby={headingId}
      className={`${backgroundClassName} px-6 py-20 scroll-mt-16`}
    >
      <div className="mx-auto max-w-6xl text-center">
        <h2 id={headingId} className="mb-4 text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl dark:text-white">
          {title}
        </h2>
        <p className="mx-auto mb-12 max-w-2xl text-base text-gray-600 dark:text-slate-300">{description}</p>

        <div className="grid gap-6 text-left sm:grid-cols-2 md:grid-cols-3">
          {items.map((item) => (
            <FeatureCard
              key={item.title}
              title={item.title}
              description={item.description}
              bordered={borderedCards}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
